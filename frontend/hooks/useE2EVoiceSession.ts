import { useCallback, useEffect, useRef, useState } from "react";
import { getWsBase } from "@/services/api/base";

type ConnectionStatus = "connecting" | "connected" | "disconnected";

type UseE2EVoiceSession = {
  connectionStatus: ConnectionStatus;
  error: string | null;
  isMuted: boolean;
  isAiSpeaking: boolean;
  disconnect: () => Promise<void>;
  toggleMute: () => void;
};

const TARGET_SAMPLE_RATE = 16000;
const PLAYBACK_SAMPLE_RATE = 24000;
const VAD_THRESHOLD = 0.01;
const COMMIT_SILENCE_MS = 700;
const FORCE_COMMIT_MS = 1200;
const MAX_RECONNECT_DELAY_MS = 20000;

function downsampleFloat32ToInt16(input: Float32Array, inputRate: number, outputRate: number): Int16Array {
  if (inputRate === outputRate) {
    const out = new Int16Array(input.length);
    for (let i = 0; i < input.length; i += 1) {
      const sample = Math.max(-1, Math.min(1, input[i]));
      out[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }
    return out;
  }

  const ratio = inputRate / outputRate;
  const outputLength = Math.max(1, Math.floor(input.length / ratio));
  const out = new Int16Array(outputLength);
  let outputIndex = 0;
  let inputIndex = 0;

  while (outputIndex < outputLength) {
    const nextInputIndex = Math.min(input.length, Math.round((outputIndex + 1) * ratio));
    let accum = 0;
    let count = 0;
    for (let i = inputIndex; i < nextInputIndex; i += 1) {
      accum += input[i];
      count += 1;
    }
    const value = count > 0 ? accum / count : 0;
    const clamped = Math.max(-1, Math.min(1, value));
    out[outputIndex] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
    outputIndex += 1;
    inputIndex = nextInputIndex;
  }

  return out;
}

function pcm16ToBase64(pcm: Int16Array): string {
  const bytes = new Uint8Array(pcm.byteLength);
  bytes.set(new Uint8Array(pcm.buffer));
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToPcm16(base64: string): Int16Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Int16Array(bytes.buffer);
}

function extractAudioChunk(event: Record<string, unknown>): string | null {
  const direct = event.delta ?? event.audio;
  if (typeof direct === "string" && direct.length > 0) {
    return direct;
  }

  const nested = event.data;
  if (nested && typeof nested === "object") {
    const nestedAudio = (nested as Record<string, unknown>).audio;
    if (typeof nestedAudio === "string" && nestedAudio.length > 0) {
      return nestedAudio;
    }
  }

  return null;
}

export function useE2EVoiceSession(sessionId: string): UseE2EVoiceSession {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connecting");
  const [error, setError] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const captureStreamRef = useRef<MediaStream | null>(null);
  const captureContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const playbackHeadRef = useRef(0);
  const aiSpeakingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMutedRef = useRef(false);
  const lastSpeechAtRef = useRef(0);
  const hasUncommittedAudioRef = useRef(false);
  const captureStartedRef = useRef(false);
  const appendSinceCommitRef = useRef(false);
  const lastCommitAtRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);
  const manualCloseRef = useRef(false);
  const hasSentOpeningRef = useRef(false);

  const sendJson = useCallback((payload: Record<string, unknown>) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }
    ws.send(JSON.stringify(payload));
  }, []);

  const playPcmChunk = useCallback(async (base64Audio: string) => {
    const pcm = base64ToPcm16(base64Audio);
    if (pcm.length === 0) {
      return;
    }

    if (!playbackContextRef.current) {
      playbackContextRef.current = new AudioContext();
    }

    const ctx = playbackContextRef.current;
    const float32 = new Float32Array(pcm.length);
    for (let i = 0; i < pcm.length; i += 1) {
      float32[i] = pcm[i] / 0x8000;
    }

    const buffer = ctx.createBuffer(1, float32.length, PLAYBACK_SAMPLE_RATE);
    buffer.copyToChannel(float32, 0);

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);

    const now = ctx.currentTime;
    const startAt = Math.max(now + 0.02, playbackHeadRef.current);
    source.start(startAt);
    playbackHeadRef.current = startAt + buffer.duration;

    setIsAiSpeaking(true);
    if (aiSpeakingTimeoutRef.current) {
      clearTimeout(aiSpeakingTimeoutRef.current);
    }
    aiSpeakingTimeoutRef.current = setTimeout(() => setIsAiSpeaking(false), 300);
  }, []);

  const startCapture = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    captureStreamRef.current = stream;

    const context = new AudioContext();
    captureContextRef.current = context;

    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;

    processor.onaudioprocess = (event) => {
      if (isMutedRef.current) {
        return;
      }

      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        return;
      }

      const input = event.inputBuffer.getChannelData(0);
      const pcm16 = downsampleFloat32ToInt16(input, context.sampleRate, TARGET_SAMPLE_RATE);
      if (pcm16.length === 0) {
        return;
      }

      let rms = 0;
      for (let i = 0; i < input.length; i += 1) {
        rms += input[i] * input[i];
      }
      rms = Math.sqrt(rms / input.length);

      if (rms > VAD_THRESHOLD) {
        lastSpeechAtRef.current = Date.now();
        hasUncommittedAudioRef.current = true;
      }

      const audioBase64 = pcm16ToBase64(pcm16);
      sendJson({ type: "input_audio_buffer.append", audio: audioBase64 });
      appendSinceCommitRef.current = true;

      const nowMs = Date.now();
      const silenceMs = nowMs - lastSpeechAtRef.current;
      const forceCommit = appendSinceCommitRef.current && nowMs - lastCommitAtRef.current > FORCE_COMMIT_MS;
      if ((hasUncommittedAudioRef.current && silenceMs > COMMIT_SILENCE_MS) || forceCommit) {
        sendJson({ type: "input_audio_buffer.commit" });
        lastCommitAtRef.current = nowMs;
        appendSinceCommitRef.current = false;
        hasUncommittedAudioRef.current = false;
      }
    };

    source.connect(processor);
    processor.connect(context.destination);
  }, [sendJson]);

  const stopCapture = useCallback(async () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current.onaudioprocess = null;
      processorRef.current = null;
    }

    if (captureContextRef.current) {
      await captureContextRef.current.close();
      captureContextRef.current = null;
    }

    if (captureStreamRef.current) {
      captureStreamRef.current.getTracks().forEach((track) => track.stop());
      captureStreamRef.current = null;
    }
  }, []);

  const disconnect = useCallback(async () => {
    manualCloseRef.current = true;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    await stopCapture();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionStatus("disconnected");
  }, [stopCapture]);

  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const next = !prev;
      isMutedRef.current = next;
      return next;
    });
  }, []);

  useEffect(() => {
    manualCloseRef.current = false;
    reconnectAttemptRef.current = 0;

    const base = getWsBase();
    const wsUrl = `${base}/e2e/sessions/${encodeURIComponent(sessionId)}`;
    const connect = () => {
      if (manualCloseRef.current) {
        return;
      }

      setConnectionStatus("connecting");
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        setError(null);

        const sessionConfig: Record<string, unknown> = {
          modalities: ["audio", "text"],
          input_audio_format: "pcm16",
          output_audio_format: "pcm16",
          send_opening: !hasSentOpeningRef.current,
        };

        const model = process.env.NEXT_PUBLIC_VOLCENGINE_E2E_MODEL;
        if (model && model.trim().length > 0) {
          sessionConfig.model = model.trim();
        }

        if (!hasSentOpeningRef.current) {
          hasSentOpeningRef.current = true;
        }

        ws.send(JSON.stringify({ type: "session.update", session: sessionConfig }));
      };

      ws.onmessage = async (event) => {
        if (typeof event.data !== "string") {
          return;
        }

        try {
          const payload = JSON.parse(event.data) as Record<string, unknown>;
          const type = payload.type;
          if (type === "error" && typeof payload.message === "string") {
            const message = payload.message;
            if (message.includes("DialogAudioIdleTimeoutError")) {
              setError("No speech detected in time. Reconnecting call...");
              ws.close();
              return;
            }
            setError(message);
            setConnectionStatus("disconnected");
            return;
          }

          if (type === "session.ready" && !captureStartedRef.current) {
            setConnectionStatus("connected");
            reconnectAttemptRef.current = 0;
            captureStartedRef.current = true;
            try {
              await startCapture();
            } catch (captureError) {
              setError(captureError instanceof Error ? captureError.message : "Microphone initialization failed");
              setConnectionStatus("disconnected");
            }
            return;
          }

          const audioChunk = extractAudioChunk(payload);
          if (audioChunk) {
            await playPcmChunk(audioChunk);
          }
        } catch {}
      };

      ws.onerror = () => {
        setError("Voice websocket connection failed");
      };

      ws.onclose = () => {
        wsRef.current = null;
        captureStartedRef.current = false;
        if (manualCloseRef.current) {
          setConnectionStatus("disconnected");
          return;
        }
        setConnectionStatus("connecting");
        reconnectAttemptRef.current += 1;
        const delay = Math.min(1000 * reconnectAttemptRef.current, MAX_RECONNECT_DELAY_MS);
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
        }
        reconnectTimerRef.current = setTimeout(() => {
          reconnectTimerRef.current = null;
          connect();
        }, delay);
      };
    };

    connect();

    return () => {
      captureStartedRef.current = false;
      appendSinceCommitRef.current = false;
      void disconnect();
      if (aiSpeakingTimeoutRef.current) {
        clearTimeout(aiSpeakingTimeoutRef.current);
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (playbackContextRef.current) {
        void playbackContextRef.current.close();
        playbackContextRef.current = null;
      }
    };
  }, [disconnect, playPcmChunk, sendJson, sessionId, startCapture]);

  return {
    connectionStatus,
    error,
    isMuted,
    isAiSpeaking,
    disconnect,
    toggleMute,
  };
}
