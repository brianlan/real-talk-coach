import { test, expect } from "@playwright/test";
import { mockScenarioApi } from "./utils/scenario-mocks";

test.describe("Practice Room UI", () => {
  test("renders practice room with sidebar and main zone", async ({ page }) => {
    // 1. Setup Mocks
    
    // Mock Scenarios (Main Zone Content)
    await mockScenarioApi(page, [
      {
        id: "scenario-1",
        category: "Leadership",
        title: "Team Conflict Resolution",
        description: "Handle a dispute between two team members.",
        objective: "Resolve the conflict",
        aiPersona: { name: "Alex", role: "Employee", background: "N/A" },
        traineePersona: { name: "Manager", role: "Lead", background: "N/A" },
        endCriteria: [],
        skills: [],
        idleLimitSeconds: 60,
        durationLimitSeconds: 600,
        prompt: "Start",
      },
    ]);

    // Mock History/Sessions (Sidebar Content)
    await page.route("**/api/sessions?**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              id: "session-123",
              scenarioId: "scenario-1",
              status: "completed",
              startedAt: new Date().toISOString(),
            },
          ],
          total: 1,
          page: 1,
          pageSize: 20,
        }),
      });
    });

    // Mock Session Creation (for click test)
    await page.route("**/api/sessions", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          body: JSON.stringify({
            id: "new-session-456",
            scenarioId: "scenario-1",
          }),
        });
      }
    });

    // 2. Navigation
    await page.goto("/practice");

    // 3. Verify Sidebar
    const sidebar = page.locator("aside");
    await expect(sidebar).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "+ New Practice" })).toBeVisible();
    await expect(sidebar.getByRole("heading", { name: "History" })).toBeVisible();
    
    // Verify history items render
    await expect(sidebar.getByRole("link", { name: "Practice Session" })).toBeVisible();

    // 4. Verify Main Zone (Scenario Selection)
    await expect(page.getByRole("heading", { name: "Select a Scenario" })).toBeVisible();
    
    const scenarioCard = page.getByRole("button", { name: "Team Conflict Resolution" });
    await expect(scenarioCard).toBeVisible();
    await expect(scenarioCard).toContainText("Leadership");
    await expect(scenarioCard).toContainText("Handle a dispute");

    // 5. Verify Interaction (Clicking a scenario)
    await scenarioCard.click();
    
    // Expect navigation to the new session
    await expect(page).toHaveURL(/\/practice\/new-session-456/);
  });
});
