import { useCallback, useRef, useState } from "react";

type RecorderState = "idle" | "recording" | "stopped";

type UseAudioRecorder = {
  state: RecorderState;
  error: string | null;
  lastBlob: Blob | null;
  start: () => Promise<void>;
  stop: () => Promise<Blob | null>;
  reset: () => void;
};

const MAX_BYTES = 128 * 1024;

export function useAudioRecorder(): UseAudioRecorder {
  const [state, setState] = useState<RecorderState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [lastBlob, setLastBlob] = useState<Blob | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const start = useCallback(async () => {
    setError(null);
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const preferredType = "audio/webm;codecs=opus";
    const options: MediaRecorderOptions = {
      audioBitsPerSecond: 24000,
      ...(MediaRecorder.isTypeSupported(preferredType) ? { mimeType: preferredType } : {}),
    };
    const recorder = new MediaRecorder(stream, options);
    chunksRef.current = [];
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };
    recorder.start();
    mediaRecorderRef.current = recorder;
    setState("recording");
  }, []);

  const stop = useCallback(async () => {
    if (!mediaRecorderRef.current) {
      return null;
    }
    return new Promise<Blob | null>((resolve) => {
      const recorder = mediaRecorderRef.current;
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        if (blob.size > MAX_BYTES) {
          setError("Audio exceeds 128 KB. Shorten or split the turn.");
          resolve(null);
          return;
        }
        setState("stopped");
        setLastBlob(blob);
        resolve(blob);
      };
      recorder.stop();
      recorder.stream.getTracks().forEach((track) => track.stop());
    });
  }, []);

  const reset = useCallback(() => {
    setState("idle");
    setError(null);
    setLastBlob(null);
    chunksRef.current = [];
  }, []);

  return { state, error, lastBlob, start, stop, reset };
}
