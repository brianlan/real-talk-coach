import { expect, test, type Page, type TestInfo } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

function ensureEvidenceDir(testInfo: TestInfo): string {
  const dir = path.resolve(
    process.cwd(),
    "..",
    ".sisyphus",
    "evidence",
    "task-15-e2e",
    "screenshots",
    "history-transcript",
    `${testInfo.retry}-${testInfo.project.name}`
  );
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

async function capture(page: Page, testInfo: TestInfo, name: string): Promise<void> {
  const targetDir = ensureEvidenceDir(testInfo);
  await page.screenshot({ path: path.join(targetDir, `${name}.png`), fullPage: true });
}

test("history detail shows realtime transcript and interruption markers", async ({ page }) => {
  const sessionId = "realtime-session-1";
  const scenarioId = "scenario-realtime-1";

  await page.route(`**/api/sessions/${sessionId}?**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session: {
          id: sessionId,
          scenarioId,
          status: "ended",
          mode: "realtime",
          terminationReason: "manual",
          startedAt: "2026-02-14T12:00:00Z",
          endedAt: "2026-02-14T12:05:00Z",
        },
        scenario: {
          id: scenarioId,
          category: "Realtime",
          title: "Handle interruption in a phone call",
          objective: "Recover politely after barge-in.",
          skillSummaries: [],
        },
        turns: [
          {
            id: "turn-1",
            sequence: 0,
            speaker: "trainee",
            transcript: "Hi, I want to discuss timeline changes.",
            audioUrl: null,
          },
          {
            id: "turn-2",
            sequence: 1,
            speaker: "ai",
            transcript: null,
            audioUrl: null,
            isInterrupted: true,
            interruptedAtMs: 1721234567890,
          },
        ],
        evaluation: null,
      }),
    });
  });

  await page.goto(`/history/${sessionId}`);
  await expect(page).toHaveURL(new RegExp(`/history/${sessionId}$`));
  await capture(page, test.info(), "01-history-detail-loaded");

  await expect(page.getByRole("heading", { name: "Transcript" })).toBeVisible();
  await expect(page.getByText("Hi, I want to discuss timeline changes.")).toBeVisible();
  await expect(page.getByText("⚡ Interrupted")).toBeVisible();
  await expect(page.getByText("(interrupted)")).toBeVisible();
  await capture(page, test.info(), "02-transcript-with-interruption");
});
