import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import EvaluationPanel from "../../components/session/EvaluationPanel";

describe("EvaluationPanel", () => {
  it("renders completed evaluation results", () => {
    const markup = renderToStaticMarkup(
      <EvaluationPanel
        evaluation={{
          sessionId: "session-1",
          status: "completed",
          scores: [
            { skillId: "skill-1", rating: 4, note: "Good pacing" },
          ],
          summary: "Overall positive feedback.",
        }}
        skillMap={{ "skill-1": { name: "Listening", rubric: "Stay curious" } }}
      />
    );

    expect(markup).toContain("Evaluation complete");
    expect(markup).toContain("Overall positive feedback.");
    expect(markup).toContain("Listening");
    expect(markup).toContain("Rating: 4");
  });

  it("disables requeue button when not allowed", () => {
    const markup = renderToStaticMarkup(
      <EvaluationPanel
        evaluation={{
          sessionId: "session-1",
          status: "failed",
          scores: [],
          summary: null,
          lastError: "Evaluator down",
        }}
        onRequeue={() => undefined}
        requeueDisabled
      />
    );

    expect(markup).toContain("Requeue");
    expect(markup).toContain("disabled");
  });
});
