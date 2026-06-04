import { test, expect } from "@playwright/test";

const stubScenarios = [
  {
    id: "scenario-1",
    title: "Sample Scenario",
    category: "General",
    status: "draft",
    recordStatus: "active",
  },
];

const stubSkills = [
  {
    id: "skill-1",
    name: "Skill A",
    category: "Cat",
    rubric: "Evaluate communication",
    status: "active",
  },
];

test.beforeEach(async ({ page }) => {
  await page.route("**/api/admin/scenarios**", async (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ scenarios: stubScenarios }),
      });
    }
    return route.fulfill({ status: 204, body: "{}" });
  });
  await page.route("**/api/admin/skills**", async (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ skills: stubSkills }),
      });
    }
    return route.fulfill({ status: 204, body: "{}" });
  });
});

test("admin can see scenarios list page", async ({ page }) => {
  await page.goto("/admin/scenarios");
  await expect(page.getByRole("heading", { name: /scenarios/i })).toBeVisible();
});

test("admin can open new scenario form", async ({ page }) => {
  await page.goto("/admin/scenarios");
  await page.getByRole("link", { name: /new scenario/i }).click();
  await expect(page.getByRole("heading", { name: /new scenario/i })).toBeVisible();
});

test("nested scenario create works without skill checkboxes", async ({ page }) => {
  let createdPayload: any = null;
  await page.route("**/api/admin/scenarios", async (route) => {
    if (route.request().method() === "POST") {
      createdPayload = route.request().postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ id: "mock-scenario-id", ...createdPayload }),
      });
    }
    return route.continue();
  });

  await page.goto("/admin/scenarios/new");
  
  await page.getByLabel(/title/i).fill("Request a Salary Increase");
  await page.getByLabel(/slug/i).fill("salary-raise");
  await page.getByLabel(/domain/i).fill("Workplace");
  await page.getByLabel(/scenario type/i).fill("Negotiation");
  await page.getByLabel(/difficulty/i).selectOption("Medium");
  await page.getByLabel(/conflict level/i).selectOption("Medium");
  await page.getByRole("spinbutton", { name: "Duration (min)" }).fill("10");

  await page.locator('div:has-text("Trainee Persona")').last().locator('input[placeholder="Name"]').fill("Alex");
  await page.locator('div:has-text("AI Persona")').last().locator('input[placeholder="Name"]').fill("Jordan");
  await page.locator("label:has-text('Situation') textarea").fill("Test Situation");
  await page.locator('select').first().selectOption({ index: 0 });
  
  await page.getByRole("button", { name: /save/i }).click();

  await expect.poll(() => createdPayload).toBeTruthy();
  expect(createdPayload.metadata.title).toBe("Request a Salary Increase");
  expect(createdPayload.metadata.slug).toBe("salary-raise");
  expect(createdPayload.simulationConfig).toBeDefined();
  expect(createdPayload.simulationConfig.ai.name).toBe("Jordan");
  expect(createdPayload.evaluationConfig).toBeDefined();
});
