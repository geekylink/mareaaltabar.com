import { test, expect } from '@playwright/test';

test('the menu is server-rendered and the prices are right', async ({ page, request }) => {
  // What a crawler or a visitor without JavaScript receives.
  const response = await request.get('/menu');
  expect(response.ok()).toBeTruthy();
  const html = await response.text();
  expect(html).toContain('Cuba Libre');
  expect(html).toContain('$4.00');

  await page.goto('/menu');

  const cuba = page.locator('.item').filter({ hasText: 'Cuba Libre' });
  // The SPA replaces the server-rendered block rather than stacking a second.
  await expect(cuba).toHaveCount(1);
  await expect(cuba.locator('.price')).toHaveText('$4.00');

  await expect(page.getByRole('heading', { name: 'Beer', exact: true })).toBeVisible();
  await expect(
    page.locator('.item').filter({ hasText: 'Club Personal' }).locator('.price')
  ).toHaveText('$2.50');
});
