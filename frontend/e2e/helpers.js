import { expect } from '@playwright/test';

// Credentials created by e2e/start-server.sh in the throwaway database.
export const ADMIN_USERNAME = 'e2e';
export const ADMIN_PASSWORD = 'e2e-test-pass';

export async function login(page) {
  await page.goto('/admin/login');
  await page.locator('#username').fill(ADMIN_USERNAME);
  await page.locator('#password').fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/admin$/);
}

// Save one item's price from /admin/menu and wait for the row to be stored.
export async function setMenuItemPrice(page, itemName, price) {
  await page.goto('/admin/menu');

  const item = page.locator('details.item').filter({ hasText: itemName }).first();
  await item.locator('summary').click();
  await item.locator('input[data-field="price"]').fill(price);

  const saved = page.waitForResponse(
    (response) =>
      response.url().includes('/api/menu/items/') &&
      response.request().method() === 'PUT' &&
      response.ok()
  );
  await item.locator('[data-action="save-item"]').click();
  await saved;

  await expect(page.locator('#global-status')).toHaveText('Saved');
}
