import { test, expect } from '@playwright/test';

test('the language switch changes the menu and survives a reload', async ({ page }) => {
  await page.goto('/menu');

  await page.locator('select.lang').selectOption('es');
  await expect(page.locator('html')).toHaveAttribute('lang', 'es');
  await expect(page.getByRole('heading', { name: 'Cerveza', exact: true })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('lang'))).toBe('es');

  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang', 'es');
  await expect(page.getByRole('heading', { name: 'Cerveza', exact: true })).toBeVisible();

  await page.locator('select.lang').selectOption('en');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('heading', { name: 'Beer', exact: true })).toBeVisible();
});
