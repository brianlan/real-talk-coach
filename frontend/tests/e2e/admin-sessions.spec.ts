import { test, expect } from "@playwright/test";

test("admin can see sessions list page", async ({ page }) => {
  await page.goto("/admin/sessions");
  await expect(page.getByRole("heading", { name: /sessions/i })).toBeVisible();
});
