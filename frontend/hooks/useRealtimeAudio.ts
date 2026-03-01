import { useCallback, useEffect, useRef, useState } from "react";
import VERTC, { IRTCEngine, onUserJoinedEvent } from "@volcengine/rtc";
import { useVolcengineRTC } from "./useVolcengineRTC";

type AudioState = {
  isListening: boolean;
  isSpeaking: boolean;
  isAiSpeaking: boolean;
  isMuted: boolean;
};

type UseRealtimeAudio = {
  toggleMute: () => void;
  setMute: (muted: boolean) => void;
} & AudioState;

const AUDIO_LEVEL_THRESHOLD = 50;

export function useRealtimeAudio(): UseRealtimeAudio {
  const { engine, isConnected } = useVolcengineRTC();
  
  const [audioState, setAudioState] = useState<AudioState>({
    isListening: false,
    isSpeaking: false,
    isAiSpeaking: false,
    isMuted: false,
  });

  const isMutedRef = useRef(false);
  const aiUserIdRef = useRef<number | null>(null);

  const updateAudioState = useCallback((updates: Partial<AudioState>) => {
    setAudioState((prev) => ({ ...prev, ...updates }));
  }, []);

  const handleAudioVolumeIndication = useCallback(
    (speakers: any[]) => {
      let localLevel = 0;
      let aiLevel = 0;

      speakers.forEach((speaker) => {
        if (speaker.uid <= 1) {
          localLevel = speaker.volume;
        }
        if (aiUserIdRef.current && speaker.uid === aiUserIdRef.current) {
          aiLevel = speaker.volume;
        }
      });

      const isListening = localLevel > AUDIO_LEVEL_THRESHOLD && !isMutedRef.current;
      const isAiSpeaking = aiLevel > AUDIO_LEVEL_THRESHOLD;
      const isSpeaking = isListening || isAiSpeaking;

      updateAudioState({
        isListening,
        isAiSpeaking,
        isSpeaking,
      });
    },
    [updateAudioState]
  );

  const handleUserJoined = useCallback((event: onUserJoinedEvent) => {
    console.log("[RealtimeAudio] User joined:", event.userInfo?.userId);
    if (event.userInfo?.userId === "ai_agent") {
      aiUserIdRef.current = 1;
    }
  }, []);

  useEffect(() => {
    if (!isConnected) {
      updateAudioState({
        isListening: false,
        isSpeaking: false,
        isAiSpeaking: false,
      });
    }
  }, [isConnected, updateAudioState]);

  useEffect(() => {
    if (!engine) {
      return;
    }

    const cleanupHandlers: (() => void)[] = [];

    const onUserJoinedHandler = (event: onUserJoinedEvent) => {
      handleUserJoined(event);
    };

    const onAudioVolumeHandler = (event: any) => {
      handleAudioVolumeIndication(event.speakers);
    };

    engine.on(VERTC.events.onUserJoined, onUserJoinedHandler);
    engine.on(VERTC.events.onAudioVolumeIndication, onAudioVolumeHandler);

    cleanupHandlers.push(() => {
      engine.off(VERTC.events.onUserJoined, onUserJoinedHandler);
      engine.off(VERTC.events.onAudioVolumeIndication, onAudioVolumeHandler);
    });

    return () => {
      cleanupHandlers.forEach((cleanup) => cleanup());
    };
  }, [engine, handleUserJoined, handleAudioVolumeIndication]);

  const setMute = useCallback(
    (muted: boolean) => {
      isMutedRef.current = muted;
      updateAudioState({ isMuted: muted });
      console.log("[RealtimeAudio] Microphone", muted ? "muted" : "unmuted");
    },
    [updateAudioState]
  );

  const toggleMute = useCallback(() => {
    setMute(!audioState.isMuted);
  }, [audioState.isMuted, setMute]);

  return {
    isListening: audioState.isListening,
    isSpeaking: audioState.isSpeaking,
    isAiSpeaking: audioState.isAiSpeaking,
    isMuted: audioState.isMuted,
    toggleMute,
    setMute,
  };
}
