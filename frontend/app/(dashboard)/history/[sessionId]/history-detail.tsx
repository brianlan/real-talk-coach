"use client";

import { useEffect, useMemo, useState } from "react";

import EvaluationPanel from "@/components/session/EvaluationPanel";
import PracticeAgainButton from "@/components/history/PracticeAgainButton";
import { fetchHistoryDetail } from "@/services/api/history";
import { requeueEvaluation } from "@/services/api/evaluationClient";
import { useUser } from "@/hooks/useUser";

type HistoryDetailProps = {
  sessionId: string;
  initialDetail: any;
};

export default function HistoryDetail({ sessionId, initialDetail }: HistoryDetailProps) {
  const { user } = useUser();
  const [detail, setDetail] = useState(initialDetail);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [requeueing, setRequeueing] = useState(false);
  const [expiredTurns, setExpiredTurns] = useState<Set<string>>(new Set());

  useEffect(() => {
    setDetail(initialDetail);
  }, [initialDetail]);

  const session = detail?.session;
  const isRealtime = session?.mode === "realtime";

  const skillMap = useMemo(() => {
    const summaries = detail?.scenario?.skillSummaries ?? [];
    return summaries.reduce(
      (acc: Record<string, { name: string; rubric?: string }>, skill: any) => {
        acc[skill.skillId] = { name: skill.name, rubric: skill.rubric };
        return acc;
      },
      {} as Record<string, { name: string; rubric?: string }>
    );
  }, [detail]);

  const refreshDetail = async () => {
    if (refreshing) {
      return;
    }
    setRefreshing(true);
    setError(null);
    try {
      const next = await fetchHistoryDetail(sessionId, 2, user?.id);
      setDetail(next);
      setExpiredTurns(new Set());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setRefreshing(false);
    }
  };

  const handleRequeue = async () => {
    if (requeueing) {
      return;
    }
    setRequeueing(true);
    setError(null);
    try {
      const evaluation = await requeueEvaluation(sessionId);
      setDetail((prev: any) => ({ ...prev, evaluation }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setRequeueing(false);
    }
  };

  return (
    <main style={{ padding: "48px 24px" }}>
      <section style={{ maxWidth: 900, margin: "0 auto" }}>
        <header style={{ marginBottom: 24 }}>
          <p style={{ textTransform: "uppercase", letterSpacing: 2, fontSize: 12 }}>
            History Detail
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <h1 style={{ fontSize: 36, margin: 0 }}>
              {detail?.scenario?.title ?? "Session detail"}
            </h1>
            {isRealtime ? (
              <span
                style={{
                  padding: "4px 12px",
                  borderRadius: 999,
                  background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                  color: "white",
                  fontSize: 11,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: 1,
                }}
              >
                Realtime
              </span>
            ) : (
              <span
                style={{
                  padding: "4px 12px",
                  borderRadius: 999,
                  background: "#e0d7cb",
                  color: "#2f2a24",
                  fontSize: 11,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: 1,
                }}
              >
                Turn-based
              </span>
            )}
          </div>
          <p style={{ maxWidth: 640 }}>
            {detail?.scenario?.objective ?? "Review the conversation outcomes."}
          </p>
        </header>

        <div
          style={{
            borderRadius: 20,
            padding: 24,
            border: "1px solid #e0d7cb",
            background: "rgba(255,255,255,0.85)",
            marginBottom: 24,
          }}
        >
          <h2 style={{ marginTop: 0 }}>Transcript</h2>
          <div style={{ display: "grid", gap: 12 }}>
            {(detail?.turns ?? []).map((turn: any) => (
              <div
                key={turn.id}
                style={{
                  padding: 16,
                  borderRadius: 12,
                  background: turn.speaker === "ai" ? "#f3eadf" : "#e9eef3",
                  position: "relative",
                  opacity: turn.isInterrupted ? 0.7 : 1,
                }}
              >
                {turn.isInterrupted ? (
                  <div
                    style={{
                      position: "absolute",
                      top: 8,
                      right: 8,
                      padding: "2px 8px",
                      borderRadius: 4,
                      background: "#ff6b6b",
                      color: "white",
                      fontSize: 10,
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: 0.5,
                    }}
                    title={`Interrupted at ${turn.interruptedAtMs}ms`}
                  >
                    ⚡ Interrupted
                  </div>
                ) : null}
                <strong style={{ textTransform: "capitalize" }}>{turn.speaker}</strong>
                <p style={{ margin: "6px 0 0" }}>
                  {turn.transcript ?? (turn.isInterrupted ? "(interrupted)" : "(transcript pending)")}
                </p>
                {turn.audioUrl ? (
                  <div style={{ marginTop: 10 }}>
                    <audio
                      controls
                      src={turn.audioUrl}
                      onError={() => {
                        setExpiredTurns((prev) => {
                          const next = new Set(prev);
                          next.add(turn.id);
                          return next;
                        });
                      }}
                      preload="none"
                    />
                    {expiredTurns.has(turn.id) ? (
                      <p style={{ margin: "6px 0 0", color: "#b24332" }}>
                        Audio link expired. Refresh to get a new link.
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16, display: "flex", gap: 12, flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={refreshDetail}
              disabled={refreshing}
              style={{
                padding: "8px 14px",
                borderRadius: 999,
                border: "1px solid #2f2a24",
                background: refreshing ? "#e0d7cb" : "transparent",
                color: "#2f2a24",
                cursor: refreshing ? "not-allowed" : "pointer",
              }}
            >
              {refreshing ? "Refreshing..." : "Refresh audio links"}
            </button>
            {error ? <p style={{ margin: 0, color: "#b24332" }}>{error}</p> : null}
          </div>
        </div>

        <div style={{ display: "grid", gap: 16 }}>
          <EvaluationPanel
            evaluation={detail?.evaluation ?? null}
            skillMap={skillMap}
            onRequeue={handleRequeue}
            requeueDisabled={requeueing}
          />
          <PracticeAgainButton sessionId={sessionId} />
        </div>
      </section>
    </main>
  );
}
