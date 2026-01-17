"use client";

type EvaluationScore = {
  skillId: string;
  rating: number;
  note: string;
};

type Evaluation = {
  sessionId: string;
  status: "pending" | "running" | "failed" | "completed";
  scores: EvaluationScore[];
  summary?: string | null;
  evaluatorModel?: string | null;
  attempts?: number | null;
  lastError?: string | null;
};

type SkillMeta = {
  name: string;
  rubric?: string | null;
};

type EvaluationPanelProps = {
  evaluation: Evaluation | null;
  skillMap?: Record<string, SkillMeta>;
  onRequeue?: () => void;
  requeueDisabled?: boolean;
};

export default function EvaluationPanel({
  evaluation,
  skillMap = {},
  onRequeue,
  requeueDisabled = false,
}: EvaluationPanelProps) {
  if (!evaluation) {
    return (
      <section
        style={{
          borderRadius: 16,
          padding: 18,
          border: "1px solid #e0d7cb",
          background: "#fffaf4",
        }}
      >
        <strong>Evaluation pending</strong>
        <p style={{ margin: "6px 0 0" }}>
          Finish the session to see coaching feedback.
        </p>
      </section>
    );
  }

  const isFailed = evaluation.status === "failed";
  const isCompleted = evaluation.status === "completed";

  return (
    <section
      style={{
        borderRadius: 18,
        padding: 20,
        border: "1px solid #e0d7cb",
        background: isFailed ? "#fff1f0" : "#fffaf4",
      }}
    >
      <header style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <strong style={{ display: "block", marginBottom: 4 }}>
            Evaluation {isCompleted ? "complete" : "status"}
          </strong>
          <span style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: 1 }}>
            {evaluation.status}
          </span>
        </div>
        {onRequeue ? (
          <button
            type="button"
            onClick={onRequeue}
            disabled={!isFailed || requeueDisabled}
            style={{
              padding: "8px 14px",
              borderRadius: 999,
              border: "1px solid #2f2a24",
              background: isFailed ? "#2f2a24" : "#e0d7cb",
              color: isFailed ? "#f7f0e6" : "#6a5f54",
              cursor: !isFailed || requeueDisabled ? "not-allowed" : "pointer",
            }}
          >
            Requeue
          </button>
        ) : null}
      </header>

      {evaluation.lastError && isFailed ? (
        <p style={{ marginTop: 12, color: "#b24332" }}>{evaluation.lastError}</p>
      ) : null}

      {isCompleted ? (
        <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
          {evaluation.summary ? (
            <p style={{ margin: 0 }}>{evaluation.summary}</p>
          ) : null}
          <div style={{ display: "grid", gap: 10 }}>
            {evaluation.scores.map((score) => (
              <div
                key={score.skillId}
                style={{
                  borderRadius: 12,
                  padding: 12,
                  background: "#f3eadf",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{skillMap[score.skillId]?.name ?? score.skillId}</strong>
                  <span>Rating: {score.rating}</span>
                </div>
                <p style={{ margin: "6px 0 0" }}>{score.note}</p>
                {skillMap[score.skillId]?.rubric ? (
                  <p style={{ margin: "6px 0 0", color: "#6a5f54", fontSize: 12 }}>
                    {skillMap[score.skillId]?.rubric}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p style={{ marginTop: 12 }}>
          {isFailed
            ? "Evaluation failed. You can retry the evaluator."
            : "Evaluation is running. Check back in a moment."}
        </p>
      )}
    </section>
  );
}
