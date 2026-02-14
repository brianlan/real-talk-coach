import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('Sign-in page renders with GitHub button', async ({ page }) => {
    await page.goto('/signin');
    
    await expect(page.getByRole('heading', { name: 'Sign In', level: 1 })).toBeVisible();
    
    const githubButton = page.getByRole('button', { name: 'Sign in with GitHub' });
    await expect(githubButton).toBeVisible();
    await expect(githubButton).toBeEnabled();
  });

  test('Clicking GitHub button initiates OAuth redirect', async ({ page }) => {
    await page.goto('/signin');
    const githubButton = page.getByRole('button', { name: 'Sign in with GitHub' });
    
    const requestPromise = page.waitForRequest(req => req.url().includes('github.com'));
    
    await githubButton.click();
    
    const request = await requestPromise;
    expect(request.url()).toContain('github.com');
  });
});
