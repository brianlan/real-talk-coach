import type { Page } from "@playwright/test";

export type ScenarioMock = {
  id: string;
  category: string;
  title: string;
  description: string;
  objective: string;
  aiPersona: { name: string; role: string; background: string };
  traineePersona: { name: string; role: string; background: string };
  endCriteria: string[];
  skills: string[];
  skillSummaries?: unknown[];
  idleLimitSeconds: number;
  durationLimitSeconds: number;
  prompt: string;
};

export async function mockScenarioApi(
  page: Page,
  scenarios: ScenarioMock[]
) {
  await page.route("**/api/scenarios**", async (route) => {
    const url = route.request().url();
    const isDetail = url.includes("/api/scenarios/");
    if (isDetail) {
      const id = url.split("/api/scenarios/")[1]?.split("?")[0] ?? "";
      const scenario = scenarios.find((item) => item.id === id);
      if (!scenario) {
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({ detail: "not found" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(scenario),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: scenarios }),
    });
  });
}
