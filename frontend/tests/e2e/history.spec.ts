import { test, expect } from "@playwright/test";

test("browse history and practice again", async ({ page }) => {
  await page.route("**/api/sessions?**", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "session-1",
            scenarioId: "scenario-1",
            status: "ended",
            startedAt: "2025-01-01T00:00:00Z",
            endedAt: "2025-01-01T00:10:00Z",
          },
        ],
        page: 1,
        pageSize: 20,
        total: 1,
      }),
    });
  });

  await page.route("**/api/scenarios/scenario-1", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "scenario-1",
        category: "Feedback",
        title: "Give feedback",
        description: "Scenario description",
        objective: "Practice feedback",
        aiPersona: { name: "Alex", role: "PM", background: "Test" },
        traineePersona: { name: "You", role: "Lead", background: "Test" },
        endCriteria: ["End"],
        skills: [],
        skillSummaries: [],
        idleLimitSeconds: 8,
        durationLimitSeconds: 300,
        prompt: "Prompt",
      }),
    });
  });

  await page.route("**/api/sessions/session-1?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session: {
          id: "session-1",
          scenarioId: "scenario-1",
          status: "ended",
          terminationReason: "manual",
          clientSessionStartedAt: "2025-01-01T00:00:00Z",
          startedAt: "2025-01-01T00:00:00Z",
          endedAt: "2025-01-01T00:10:00Z",
          totalDurationSeconds: 600,
          idleLimitSeconds: 8,
          durationLimitSeconds: 300,
          wsChannel: "/ws/sessions/session-1",
          objectiveStatus: "unknown",
          objectiveReason: null,
          evaluationId: "eval-1",
        },
        scenario: {
          id: "scenario-1",
          category: "Feedback",
          title: "Give feedback",
          description: "Scenario description",
          objective: "Practice feedback",
          aiPersona: { name: "Alex", role: "PM", background: "Test" },
          traineePersona: { name: "You", role: "Lead", background: "Test" },
          endCriteria: ["End"],
          skills: [],
          skillSummaries: [],
          idleLimitSeconds: 8,
          durationLimitSeconds: 300,
          prompt: "Prompt",
        },
        turns: [
          {
            id: "turn-1",
            sessionId: "session-1",
            sequence: 0,
            speaker: "ai",
            transcript: "Hello",
            audioFileId: "file-1",
            audioUrl: "https://example.com/audio.mp3",
            asrStatus: null,
            createdAt: "2025-01-01T00:00:00Z",
            startedAt: "2025-01-01T00:00:00Z",
            endedAt: "2025-01-01T00:00:00Z",
            context: null,
            latencyMs: 120,
          },
        ],
        evaluation: {
          sessionId: "session-1",
          status: "completed",
          scores: [],
          summary: "Nice work",
          evaluatorModel: "gpt-5-mini",
          attempts: 1,
          lastError: null,
          queuedAt: "2025-01-01T00:00:00Z",
          completedAt: "2025-01-01T00:00:10Z",
        },
      }),
    });
  });

  await page.route("**/api/sessions/session-1/practice-again", async (route) => {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        id: "session-2",
        scenarioId: "scenario-1",
        status: "pending",
      }),
    });
  });

  await page.goto("/history");
  await expect(page.getByText("Give feedback")).toBeVisible();
  await page.getByText("Give feedback").click();

  await expect(page.getByText("Transcript")).toBeVisible();
  await expect(page.getByText("Nice work")).toBeVisible();

  await page.getByRole("button", { name: /practice again/i }).click();
  await expect(page).toHaveURL(/\/practice\/session-2/);
});
