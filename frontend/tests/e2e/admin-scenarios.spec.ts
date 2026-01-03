import { test, expect } from "@playwright/test";

test("admin can see scenarios list page", async ({ page }) => {
  await page.goto("/admin/scenarios");
  await expect(page.getByRole("heading", { name: /scenarios/i })).toBeVisible();
});

test("admin can open new scenario form", async ({ page }) => {
  await page.goto("/admin/scenarios");
  await page.getByRole("button", { name: /new scenario/i }).click();
  await expect(page.getByRole("heading", { name: /new scenario/i })).toBeVisible();
});
