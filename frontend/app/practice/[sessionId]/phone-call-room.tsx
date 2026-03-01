"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useVolcengineRTC } from "@/hooks/useVolcengineRTC";
import { useRealtimeAudio } from "@/hooks/useRealtimeAudio";
import { getApiBase } from "@/services/api/base";
import { manualStopSession } from "@/services/api/sessions";

const apiBase = getApiBase();

type ConnectionStatus = "connecting" | "connected" | "disconnected";

type RealtimeTokenResponse = {
  token: string;
  room_id: string;
  app_id: string;
};

export default function PhoneCallRoom({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const { aiStatus, joinRoom, leaveRoom } = useVolcengineRTC();
  const { isAiSpeaking, isMuted, toggleMute } = useRealtimeAudio();

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connecting");
  const [callDuration, setCallDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isEnding, setIsEnding] = useState(false);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let isMounted = true;

    const initConnection = async () => {
      try {
        setConnectionStatus("connecting");
        setError(null);

        const response = await fetch(`${apiBase}/api/realtime/token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            user_id: "1",
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || "Failed to fetch RTC token");
        }

        const data: RealtimeTokenResponse = await response.json();

        if (!isMounted) return;

        await joinRoom(data.token, data.room_id, "1");
        setConnectionStatus("connected");

        timerRef.current = setInterval(() => {
          setCallDuration((prev) => prev + 1);
        }, 1000);
      } catch (err) {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : "Connection failed");
        setConnectionStatus("disconnected");
      }
    };

    initConnection();

    return () => {
      isMounted = false;
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [sessionId, joinRoom]);

  useEffect(() => {
    if (aiStatus === "joined") {
      setConnectionStatus("connected");
    } else if (aiStatus === "leaving" || aiStatus === "left") {
      setConnectionStatus("disconnected");
    }
  }, [aiStatus]);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      void leaveRoom();
    };
  }, [leaveRoom]);

  const formatDuration = useCallback((seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }, []);

  const handleEndCall = useCallback(async () => {
    if (isEnding) return;
    setIsEnding(true);

    try {
      await fetch(`${apiBase}/api/realtime/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      await manualStopSession(sessionId, "manual");
      await leaveRoom();
      router.push("/");
    } catch (err) {
      console.error("Error ending call:", err);
      router.push("/");
    }
  }, [sessionId, isEnding, leaveRoom, router]);

  const handleMuteToggle = useCallback(() => {
    toggleMute();
  }, [toggleMute]);

  const SpeakingIndicator = ({ isSpeaking }: { isSpeaking: boolean }) => {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "4px",
          height: "40px",
        }}
      >
        {[1, 2, 3, 4, 5].map((bar) => (
          <div
            key={bar}
            style={{
              width: "6px",
              borderRadius: "3px",
              background: isSpeaking
                ? "linear-gradient(180deg, #ef4444 0%, #dc2626 100%)"
                : "rgba(239, 68, 68, 0.3)",
              height: isSpeaking ? `${16 + Math.random() * 24}px` : "8px",
              transition: isSpeaking ? "height 0.1s ease, background 0.2s ease" : "height 0.3s ease, background 0.3s ease",
              animation: isSpeaking ? `pulse 0.5s ease-in-out infinite alternate ${bar * 0.1}s` : "none",
            }}
          />
        ))}
      </div>
    );
  };

  const AIAvatar = () => {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "16px",
        }}
      >
        <div
          style={{
            width: "120px",
            height: "120px",
            borderRadius: "50%",
            background: isAiSpeaking
              ? "linear-gradient(135deg, #fca5a5 0%, #ef4444 100%)"
              : "linear-gradient(135deg, #fcd34d 0%, #f59e0b 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "48px",
            boxShadow: isAiSpeaking
              ? "0 0 30px rgba(239, 68, 68, 0.6), 0 0 60px rgba(239, 68, 68, 0.3)"
              : "0 0 20px rgba(245, 158, 11, 0.4)",
            transition: "all 0.3s ease",
            animation: isAiSpeaking ? "glow 1s ease-in-out infinite alternate" : "none",
          }}
        >
          🤖
        </div>
        <div style={{ textAlign: "center" }}>
          <p style={{ fontSize: "18px", fontWeight: 600, margin: 0, color: "#1f2937" }}>
            AI Coach
          </p>
          <p style={{ fontSize: "14px", color: "#6b7280", margin: "4px 0 0" }}>
            {aiStatus === "joined" ? "Connected" : aiStatus === "joining" ? "Connecting..." : "Disconnected"}
          </p>
        </div>
        <SpeakingIndicator isSpeaking={isAiSpeaking} />
      </div>
    );
  };

  const UserIndicator = () => {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "8px",
          marginTop: "24px",
        }}
      >
        <div
          style={{
            width: "80px",
            height: "80px",
            borderRadius: "50%",
            background: isMuted
              ? "linear-gradient(135deg, #9ca3af 0%, #6b7280 100%)"
              : "linear-gradient(135deg, #60a5fa 0%, #3b82f6 100%)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "32px",
            boxShadow: isMuted ? "none" : "0 0 20px rgba(59, 130, 246, 0.4)",
            transition: "all 0.3s ease",
          }}
        >
          {isMuted ? "🔇" : "👤"}
        </div>
        <p style={{ fontSize: "14px", color: "#6b7280", margin: 0 }}>
          {isMuted ? "Muted" : "You"}
        </p>
        <SpeakingIndicator isSpeaking={!isMuted && !isAiSpeaking} />
      </div>
    );
  };

  const ConnectionBadge = () => {
    const statusColors = {
      connecting: { bg: "#fef3c7", border: "#f59e0b", text: "#92400e" },
      connected: { bg: "#d1fae5", border: "#10b981", text: "#065f46" },
      disconnected: { bg: "#fee2e2", border: "#ef4444", text: "#991b1b" },
    };

    const colors = statusColors[connectionStatus];

    return (
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "8px",
          padding: "6px 12px",
          borderRadius: "999px",
          background: colors.bg,
          border: `1px solid ${colors.border}`,
          color: colors.text,
          fontSize: "13px",
          fontWeight: 500,
        }}
      >
        <div
          style={{
            width: "8px",
            height: "8px",
            borderRadius: "50%",
            background: colors.border,
            animation: connectionStatus === "connecting" ? "blink 1s ease-in-out infinite" : "none",
          }}
        />
        {connectionStatus === "connecting"
          ? "Connecting..."
          : connectionStatus === "connected"
          ? "Connected"
          : "Disconnected"}
      </div>
    );
  };

  return (
    <>
      <style jsx global>{`
        @keyframes pulse {
          0% {
            transform: scaleY(0.8);
          }
          100% {
            transform: scaleY(1.2);
          }
        }
        @keyframes glow {
          0% {
            box-shadow: 0 0 20px rgba(239, 68, 68, 0.4), 0 0 40px rgba(239, 68, 68, 0.2);
          }
          100% {
            box-shadow: 0 0 40px rgba(239, 68, 68, 0.7), 0 0 80px rgba(239, 68, 68, 0.4);
          }
        }
        @keyframes blink {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }
      `}</style>

      <main
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "24px",
          background: "linear-gradient(180deg, #fef2f2 0%, #fff7ed 50%, #fef3c7 100%)",
        }}
      >
        <header
          style={{
            width: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "12px",
            paddingTop: "16px",
          }}
        >
          <ConnectionBadge />
          <div
            style={{
              fontSize: "32px",
              fontWeight: 700,
              color: "#1f2937",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {formatDuration(callDuration)}
          </div>
          {error && (
            <p style={{ color: "#dc2626", fontSize: "14px", margin: 0 }}>{error}</p>
          )}
        </header>

        <section
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
          }}
        >
          <AIAvatar />
          <UserIndicator />
        </section>

        <footer
          style={{
            width: "100%",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: "32px",
            paddingBottom: "32px",
          }}
        >
          <button
            type="button"
            onClick={handleMuteToggle}
            disabled={connectionStatus !== "connected"}
            style={{
              width: "64px",
              height: "64px",
              borderRadius: "50%",
              border: "none",
              background: isMuted
                ? "linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)"
                : "linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%)",
              cursor: connectionStatus === "connected" ? "pointer" : "not-allowed",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "28px",
              boxShadow: isMuted
                ? "0 4px 12px rgba(245, 158, 11, 0.4)"
                : "0 4px 12px rgba(156, 163, 175, 0.4)",
              transition: "all 0.2s ease",
              opacity: connectionStatus === "connected" ? 1 : 0.5,
            }}
            aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
          >
            {isMuted ? "🔇" : "🎤"}
          </button>

          <button
            type="button"
            onClick={handleEndCall}
            disabled={isEnding || connectionStatus === "connecting"}
            style={{
              width: "80px",
              height: "80px",
              borderRadius: "50%",
              border: "none",
              background: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
              cursor: isEnding || connectionStatus === "connecting" ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "32px",
              boxShadow: "0 6px 20px rgba(239, 68, 68, 0.5)",
              transition: "all 0.2s ease",
              transform: isEnding ? "scale(0.95)" : "scale(1)",
            }}
            aria-label="End call"
          >
            📞
          </button>

          <div style={{ width: "64px", height: "64px" }} />
        </footer>
      </main>
    </>
  );
}
