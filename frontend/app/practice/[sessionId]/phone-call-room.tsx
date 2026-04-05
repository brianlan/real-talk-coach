"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { manualStopSession, manualStopSessionBestEffort } from "@/services/api/sessions";
import { useE2EVoiceSession } from "@/hooks/useE2EVoiceSession";

function isDebugPromptsEnabled(): boolean {
  return process.env.NEXT_PUBLIC_PHONE_CALL_ROOM_DEBUG_PROMPTS === "1";
}

export default function PhoneCallRoom({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const {
    connectionStatus,
    error,
    isMuted,
    isAiSpeaking,
    debugSystemPrompt,
    debugOpeningText,
    disconnect,
    toggleMute,
  } = useE2EVoiceSession(sessionId);

  const [callDuration, setCallDuration] = useState(0);
  const [isEnding, setIsEnding] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const hasSentStopRef = useRef(false);
  const debugPromptsEnabled = isDebugPromptsEnabled();

  useEffect(() => {
    if (connectionStatus !== "connected") {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    timerRef.current = setInterval(() => {
      setCallDuration((prev) => prev + 1);
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [connectionStatus]);

  const formatDuration = useCallback((seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }, []);

  const handleEndCall = useCallback(async () => {
    if (isEnding) {
      return;
    }

    setIsEnding(true);
    hasSentStopRef.current = true;
    try {
      await disconnect();
      await manualStopSession(sessionId, "manual");
    } finally {
      router.push("/");
    }
  }, [disconnect, isEnding, router, sessionId]);

  useEffect(() => {
    const handlePageHide = () => {
      if (hasSentStopRef.current) {
        return;
      }
      hasSentStopRef.current = true;
      manualStopSessionBestEffort(sessionId, "manual");
      void disconnect();
    };

    window.addEventListener("pagehide", handlePageHide);
    window.addEventListener("beforeunload", handlePageHide);
    return () => {
      window.removeEventListener("pagehide", handlePageHide);
      window.removeEventListener("beforeunload", handlePageHide);
    };
  }, [disconnect, sessionId]);

  const SpeakingIndicator = ({ speaking }: { speaking: boolean }) => (
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
            background: speaking
              ? "linear-gradient(180deg, #ef4444 0%, #dc2626 100%)"
              : "rgba(239, 68, 68, 0.3)",
            height: speaking ? `${16 + Math.random() * 24}px` : "8px",
            transition: speaking
              ? "height 0.1s ease, background 0.2s ease"
              : "height 0.3s ease, background 0.3s ease",
            animation: speaking ? `pulse 0.5s ease-in-out infinite alternate ${bar * 0.1}s` : "none",
          }}
        />
      ))}
    </div>
  );

  const AIAvatar = () => (
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
        <p style={{ fontSize: "18px", fontWeight: 600, margin: 0, color: "#1f2937" }}>AI Coach</p>
        <p style={{ fontSize: "14px", color: "#6b7280", margin: "4px 0 0" }}>
          {connectionStatus === "connected"
            ? "Connected"
            : connectionStatus === "connecting"
            ? "Connecting..."
            : "Disconnected"}
        </p>
      </div>
      <SpeakingIndicator speaking={isAiSpeaking} />
    </div>
  );

  const UserIndicator = () => (
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
      <p style={{ fontSize: "14px", color: "#6b7280", margin: 0 }}>{isMuted ? "Muted" : "You"}</p>
      <SpeakingIndicator speaking={!isMuted} />
    </div>
  );

  const statusColors = {
    connecting: { bg: "#fef3c7", border: "#f59e0b", text: "#92400e" },
    connected: { bg: "#d1fae5", border: "#10b981", text: "#065f46" },
    disconnected: { bg: "#fee2e2", border: "#ef4444", text: "#991b1b" },
  };

  const colors = statusColors[connectionStatus];

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
          0%,
          100% {
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
          justifyContent: "center",
          padding: "24px",
          background: "linear-gradient(180deg, #fef2f2 0%, #fff7ed 50%, #fef3c7 100%)",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: debugPromptsEnabled ? "1400px" : "960px",
            display: "flex",
            gap: "24px",
            flexWrap: "wrap",
            alignItems: "stretch",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              flex: "1 1 720px",
              minWidth: "320px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "space-between",
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
              {error ? <p style={{ color: "#dc2626", fontSize: "14px", margin: 0 }}>{error}</p> : null}
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
                onClick={toggleMute}
                disabled={connectionStatus === "disconnected" || isEnding}
                style={{
                  width: "64px",
                  height: "64px",
                  borderRadius: "50%",
                  border: "none",
                  background: isMuted
                    ? "linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)"
                    : "linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%)",
                  cursor: connectionStatus === "disconnected" || isEnding ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "28px",
                  boxShadow: isMuted
                    ? "0 4px 12px rgba(245, 158, 11, 0.4)"
                    : "0 4px 12px rgba(156, 163, 175, 0.4)",
                  transition: "all 0.2s ease",
                  opacity: connectionStatus === "disconnected" || isEnding ? 0.5 : 1,
                }}
                aria-label={isMuted ? "Unmute microphone" : "Mute microphone"}
              >
                {isMuted ? "🔇" : "🎤"}
              </button>

              <button
                type="button"
                onClick={handleEndCall}
                disabled={isEnding}
                style={{
                  width: "80px",
                  height: "80px",
                  borderRadius: "50%",
                  border: "none",
                  background: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
                  cursor: isEnding ? "not-allowed" : "pointer",
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
          </div>

          {debugPromptsEnabled ? (
            <aside
              data-testid="phone-call-debug-sidebar"
              style={{
                flex: "0 1 360px",
                minWidth: "280px",
                maxWidth: "420px",
                alignSelf: "stretch",
                borderRadius: "20px",
                border: "1px solid rgba(148, 163, 184, 0.35)",
                background: "rgba(255, 255, 255, 0.78)",
                boxShadow: "0 18px 50px rgba(15, 23, 42, 0.12)",
                backdropFilter: "blur(18px)",
                padding: "20px",
                display: "grid",
                gap: "16px",
              }}
            >
              <div style={{ display: "grid", gap: "4px" }}>
                <p style={{ margin: 0, fontSize: "12px", letterSpacing: "0.08em", textTransform: "uppercase", color: "#92400e", fontWeight: 700 }}>
                  Debug prompt data
                </p>
                <p style={{ margin: 0, fontSize: "13px", color: "#6b7280" }}>
                  Visible only when NEXT_PUBLIC_PHONE_CALL_ROOM_DEBUG_PROMPTS=1.
                </p>
              </div>

              <div style={{ display: "grid", gap: "8px" }}>
                <p style={{ margin: 0, fontSize: "13px", fontWeight: 700, color: "#1f2937" }}>Initial system prompt</p>
                <div
                  style={{
                    borderRadius: "14px",
                    border: "1px solid rgba(203, 213, 225, 0.9)",
                    background: "rgba(248, 250, 252, 0.92)",
                    padding: "12px",
                    fontSize: "12px",
                    lineHeight: 1.5,
                    color: "#0f172a",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    overflowY: "auto",
                    maxHeight: "36vh",
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                  }}
                >
                  {debugSystemPrompt ?? "No debug system prompt received."}
                </div>
              </div>

              <div style={{ display: "grid", gap: "8px" }}>
                <p style={{ margin: 0, fontSize: "13px", fontWeight: 700, color: "#1f2937" }}>Opening text</p>
                <div
                  style={{
                    borderRadius: "14px",
                    border: "1px solid rgba(203, 213, 225, 0.9)",
                    background: "rgba(248, 250, 252, 0.92)",
                    padding: "12px",
                    fontSize: "13px",
                    lineHeight: 1.5,
                    color: "#0f172a",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    overflowY: "auto",
                    maxHeight: "24vh",
                  }}
                >
                  {debugOpeningText ?? "No opening text received."}
                </div>
              </div>
            </aside>
          ) : null}
        </div>
      </main>
    </>
  );
}
