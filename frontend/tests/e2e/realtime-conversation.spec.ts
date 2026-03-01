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
    "realtime-conversation",
    `${testInfo.retry}-${testInfo.project.name}`
  );
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

async function capture(page: Page, testInfo: TestInfo, name: string): Promise<void> {
  const targetDir = ensureEvidenceDir(testInfo);
  await page.screenshot({ path: path.join(targetDir, `${name}.png`), fullPage: true });
}

test("complete realtime conversation flow and view transcript in history", async ({ page }) => {
  test.skip(
    process.env.RTC_E2E_ENABLED !== "1",
    "Set RTC_E2E_ENABLED=1 with valid Volcengine credentials to run live RTC flow."
  );

  await page.goto("/");
  await capture(page, test.info(), "01-home");

  await page.getByRole("button", { name: "Start Practice" }).click();
  await expect(page).toHaveURL(/\/practice/);
  await capture(page, test.info(), "02-practice-list");

  const startButtons = page.getByRole("button", { name: "Start Practice", exact: true });
  await expect(startButtons.first()).toBeVisible();
  await startButtons.first().click();

  await expect(page).toHaveURL(/\/practice\/[^/]+$/);
  const realtimeUrl = page.url();
  const sessionId = realtimeUrl.split("/").pop() ?? "";
  expect(sessionId).not.toEqual("");
  await capture(page, test.info(), "03-phone-call-room-entered");

  await expect(page.getByText("Transcript")).toHaveCount(0);
  await expect(page.getByText("Connected")).toBeVisible({ timeout: 45_000 });
  await capture(page, test.info(), "04-rtc-connected");

  await page.getByRole("button", { name: "End call" }).click();
  await expect(page).toHaveURL("/");
  await capture(page, test.info(), "05-call-ended-home");

  await page.goto(`/history/${sessionId}`);
  await expect(page.getByRole("heading", { name: "Transcript" })).toBeVisible();
  await expect(page.getByRole("button", { name: "End call" })).toHaveCount(0);
  await capture(page, test.info(), "06-history-transcript");
});
