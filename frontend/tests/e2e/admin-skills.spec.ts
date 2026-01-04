import { test, expect } from "@playwright/test";

const stubSkills = [
  {
    id: "skill-1",
    name: "Active Skill",
    category: "Category",
    rubric: "Do great things",
    status: "active",
  },
];

test.beforeEach(async ({ page }) => {
  await page.route("**/api/admin/skills**", async (route) => {
    const method = route.request().method();
    if (method === "GET") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ skills: stubSkills }),
      });
    }
    if (method === "POST") {
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ ...stubSkills[0], id: "skill-new" }),
      });
    }
    return route.fulfill({ status: 204, body: "{}" });
  });
});

// These tests assume the admin skills pages exist and backend stubs/mocks are configured.
test("admin can see skills list page", async ({ page }) => {
  await page.goto("/admin/skills");
  await expect(page.getByRole("heading", { name: /skills/i })).toBeVisible();
});

test("admin can open create skill form", async ({ page }) => {
  await page.goto("/admin/skills");
  await page.getByRole("link", { name: /new skill/i }).click();
  await expect(page.getByRole("heading", { name: /new skill/i })).toBeVisible();
});

test("admin can submit skill form", async ({ page }) => {
  await page.goto("/admin/skills/new");
  await page.getByLabel(/name/i).fill("Skill");
  await page.getByLabel(/category/i).fill("Cat");
  await page.getByLabel(/rubric/i).fill("Rubric");
  await page.getByRole("button", { name: /save/i }).click();
  await expect(page.getByText(/saved|created/i).first()).toBeVisible();
});
