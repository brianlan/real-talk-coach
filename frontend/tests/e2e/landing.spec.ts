import { test, expect } from "@playwright/test";

test.describe("Landing Page", () => {
  test("landing page renders with title and buttons", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Real Talk Coach/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Start Practice/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Sign In/i })).toBeVisible();
  });

  test("Start Practice button navigates to /practice", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Start Practice/i }).click();
    await expect(page).toHaveURL(/\/practice/);
  });

  test("Sign In button navigates to /signin", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /Sign In/i }).click();
    await expect(page).toHaveURL(/\/signin/);
  });

  test("Anonymous user cookie is set on page load", async ({ page }) => {
    await page.goto("/");
    
    await expect.poll(async () => {
      const cookies = await page.context().cookies();
      return cookies.find(c => c.name === "rtc_user_id")?.value;
    }).toBeTruthy();
  });
});
