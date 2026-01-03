import { test, expect } from "@playwright/test";

const ADMIN_TOKEN = process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "admin-token";

// These tests assume the admin skills pages exist and backend stubs/mocks are configured.
test("admin can see skills list page", async ({ page }) => {
  await page.goto("/admin/skills");
  await expect(page.getByRole("heading", { name: /skills/i })).toBeVisible();
});

test("admin can open create skill form", async ({ page }) => {
  await page.goto("/admin/skills");
  await page.getByRole("button", { name: /new skill/i }).click();
  await expect(page.getByRole("heading", { name: /new skill/i })).toBeVisible();
});

test("admin can submit skill form", async ({ page }) => {
  await page.goto("/admin/skills/new");
  await page.getByLabel(/name/i).fill("Skill");
  await page.getByLabel(/category/i).fill("Cat");
  await page.getByLabel(/rubric/i).fill("Rubric");
  await page.getByRole("button", { name: /save/i }).click();
  await expect(page.getByText(/saved|created/i)).toBeVisible();
});
