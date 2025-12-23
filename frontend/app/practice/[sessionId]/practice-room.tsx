"use client";

import { useEffect, useMemo, useState } from "react";

import { submitTurn, connectSessionSocket, manualStopSession } from "@/services/api/sessions";
import { useAudioRecorder } from "@/services/audio/useAudioRecorder";

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const wsBase = process.env.NEXT_PUBLIC_WS_BASE ?? "ws://localhost:8000/ws";

type Turn = {
  id: string;
  sequence: number;
  speaker: string;
  transcript?: string | null;
};

type Termination = {
  reason: string;
  terminatedAt: string;
};

type SessionEvent =
  | { type: "ai_turn"; turn: Turn }
  | { type: "termination"; termination: Termination; message?: string };

export default function PracticeRoom({ sessionId }: { sessionId: string }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [termination, setTermination] = useState<Termination | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [sequence, setSequence] = useState(0);
  const [resendToken, setResendToken] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const wsUrl = useMemo(() => `${wsBase}/sessions/${sessionId}`, [sessionId]);
  const recorder = useAudioRecorder();

  useEffect(() => {
    const socket = connectSessionSocket(sessionId);
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as SessionEvent;
      if (payload.type === "ai_turn") {
        setTurns((prev) => [...prev, payload.turn]);
        setSequence(payload.turn.sequence + 1);
      }
      if (payload.type === "termination") {
        setTermination(payload.termination);
        setMessage(payload.message ?? "Session ended");
      }
    };
    return () => socket.close();
  }, [sessionId, wsUrl]);

  const manualStop = async () => {
    await manualStopSession(sessionId, "manual");
    setTermination({ reason: "manual", terminatedAt: new Date().toISOString() });
    setMessage("Session ended");
  };

  const handleRecord = async () => {
    if (recorder.state === "recording") {
      const blob = await recorder.stop();
      if (blob) {
        setResendToken(null);
      }
    } else {
      await recorder.start();
    }
  };

  const handleSend = async () => {
    if (!recorder.lastBlob || sending) {
      return;
    }
    setSending(true);
    const result = await submitTurn({
      sessionId,
      sequence,
      audioBlob: recorder.lastBlob,
      audioBase64: resendToken ?? undefined,
      startedAt: new Date().toISOString(),
      endedAt: new Date().toISOString(),
    });
    setSending(false);
    if (result.shouldResend && result.audioBase64) {
      setResendToken(result.audioBase64);
      setMessage("Audio upload failed. Please resend your turn.");
      return;
    }
    if (result.status === 202) {
      recorder.reset();
      setResendToken(null);
      setMessage(null);
    }
  };

  return (
    <main style={{ padding: "48px 24px" }}>
      <section style={{ maxWidth: 840, margin: "0 auto" }}>
        <header style={{ marginBottom: 24 }}>
          <p style={{ textTransform: "uppercase", letterSpacing: 2, fontSize: 12 }}>
            Practice Room
          </p>
          <h1 style={{ fontSize: 36, margin: "8px 0" }}>Live coaching session</h1>
          <p>Session ID: {sessionId}</p>
        </header>

        {termination ? (
          <div
            style={{
              borderRadius: 16,
              padding: 20,
              background:
                termination.reason === "qa_error" ? "#fbe9e7" : "#f6e6d3",
              border:
                termination.reason === "qa_error"
                  ? "1px solid #f5c1b6"
                  : "1px solid #e5c8a3",
              marginBottom: 24,
            }}
          >
            <strong>Session ended</strong>
            <p style={{ margin: "8px 0 0" }}>{message}</p>
            {termination.reason === "qa_error" ? (
              <button
                type="button"
                onClick={() => window.location.reload()}
                style={{
                  marginTop: 12,
                  padding: "8px 14px",
                  borderRadius: 999,
                  border: "1px solid #f5c1b6",
                  background: "#fff3ef",
                  cursor: "pointer",
                }}
              >
                Retry connection
              </button>
            ) : null}
          </div>
        ) : (
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 24 }}>
            <button
              type="button"
              onClick={handleRecord}
              style={{
                padding: "10px 18px",
                borderRadius: 999,
                border: "none",
                background: recorder.state === "recording" ? "#b24332" : "#2f2a24",
                color: "#f7f0e6",
                cursor: "pointer",
              }}
            >
              {recorder.state === "recording" ? "Stop recording" : "Record turn"}
            </button>
            <button
              type="button"
              disabled={!recorder.lastBlob || sending}
              onClick={handleSend}
              style={{
                padding: "10px 18px",
                borderRadius: 999,
                border: "1px solid #2f2a24",
                background: "transparent",
                color: "#2f2a24",
                cursor: recorder.lastBlob && !sending ? "pointer" : "not-allowed",
              }}
            >
              {sending ? "Sending..." : resendToken ? "Resend turn" : "Send turn"}
            </button>
            <button
              type="button"
              onClick={manualStop}
              style={{
                padding: "10px 18px",
                borderRadius: 999,
                border: "none",
                background: "#2f2a24",
                color: "#f7f0e6",
                cursor: "pointer",
              }}
            >
              End session
            </button>
          </div>
        )}

        {recorder.error ? (
          <p style={{ color: "#b24332", marginTop: 0 }}>{recorder.error}</p>
        ) : null}

        <div
          style={{
            borderRadius: 20,
            padding: 24,
            border: "1px solid #e0d7cb",
            background: "rgba(255,255,255,0.85)",
            display: "grid",
            gap: 16,
          }}
        >
          {turns.length === 0 ? (
            <p>No turns yet. Waiting for the AI to begin...</p>
          ) : (
            turns.map((turn) => (
              <div
                key={turn.id}
                style={{
                  padding: 16,
                  borderRadius: 12,
                  background: turn.speaker === "ai" ? "#f3eadf" : "#e9eef3",
                }}
              >
                <strong style={{ textTransform: "capitalize" }}>{turn.speaker}</strong>
                <p style={{ margin: "6px 0 0" }}>
                  {turn.transcript ?? "(transcript pending)"}
                </p>
              </div>
            ))
          )}
        </div>
      </section>
    </main>
  );
}
