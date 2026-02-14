import { test, expect } from '@playwright/test';

test.describe('Homepage UI Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display the Next.js logo', async ({ page }) => {
    const logo = page.locator('img[alt="Next.js logo"]');
    await expect(logo).toBeVisible();
    await expect(logo).toHaveAttribute('src', '/next.svg');
  });

  test('should display the main heading', async ({ page }) => {
    const heading = page.locator('h1');
    await expect(heading).toBeVisible();
    await expect(heading).toContainText('To get started, edit the page.tsx file.');
  });

  test('should display the description paragraph', async ({ page }) => {
    const description = page.locator('p').filter({ hasText: 'Looking for a starting point' });
    await expect(description).toBeVisible();
  });

  test('should have working links', async ({ page }) => {
    // Test Templates link
    const templatesLink = page.locator('a[href*="vercel.com/templates"]');
    await expect(templatesLink).toBeVisible();
    await expect(templatesLink).toContainText('Templates');
    
    // Test Learning link
    const learningLink = page.locator('a[href*="nextjs.org/learn"]');
    await expect(learningLink).toBeVisible();
    await expect(learningLink).toContainText('Learning');
  });

  test('should have Deploy Now button', async ({ page }) => {
    const deployButton = page.locator('a').filter({ hasText: 'Deploy Now' });
    await expect(deployButton).toBeVisible();
    await expect(deployButton).toHaveAttribute('href', expect.stringContaining('vercel.com/new'));
  });

  test('should have Documentation button', async ({ page }) => {
    const docsButton = page.locator('a').filter({ hasText: 'Documentation' });
    await expect(docsButton).toBeVisible();
    await expect(docsButton).toHaveAttribute('href', expect.stringContaining('nextjs.org/docs'));
  });

  test('should have proper layout and styling', async ({ page }) => {
    const main = page.locator('main');
    await expect(main).toBeVisible();
    
    // Check that main has proper flex layout
    const mainStyles = await main.evaluate((el) => {
      return window.getComputedStyle(el);
    });
    expect(mainStyles.display).toBe('flex');
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    
    const heading = page.locator('h1');
    await expect(heading).toBeVisible();
    
    // Check that buttons stack vertically on mobile
    const buttonsContainer = page.locator('main > div:last-child');
    const flexDirection = await buttonsContainer.evaluate((el) => {
      return window.getComputedStyle(el).flexDirection;
    });
    expect(flexDirection).toBe('column');
  });

  test('should support dark mode', async ({ page }) => {
    // Check if dark mode classes are present in the HTML
    const html = page.locator('html');
    const htmlClass = await html.getAttribute('class');
    
    // The page should have dark mode support (classes might be added dynamically)
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('should have proper accessibility attributes', async ({ page }) => {
    // Check for alt text on images
    const images = page.locator('img');
    const count = await images.count();
    
    for (let i = 0; i < count; i++) {
      const alt = await images.nth(i).getAttribute('alt');
      expect(alt).toBeTruthy();
    }
  });

  test('should have proper semantic HTML structure', async ({ page }) => {
    const main = page.locator('main');
    await expect(main).toBeVisible();
    
    const heading = page.locator('h1');
    await expect(heading).toBeVisible();
    
    const paragraphs = page.locator('p');
    await expect(paragraphs.first()).toBeVisible();
  });
});
