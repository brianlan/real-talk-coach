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
