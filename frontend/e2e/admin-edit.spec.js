import { test, expect } from '@playwright/test';
import { login, setMenuItemPrice } from './helpers.js';

// The Club Personal price, not Cuba Libre, so this spec does not collide with
// menu.spec.js if the order ever changes. The price is restored in `finally`, so
// the suite is safe to run twice against the same database.
test('an admin price edit reaches the public menu', async ({ page }) => {
  await login(page);

  try {
    await setMenuItemPrice(page, 'Club Personal', '2.75');

    await page.goto('/menu');
    await expect(
      page.locator('.item').filter({ hasText: 'Club Personal' }).locator('.price')
    ).toHaveText('$2.75');
  } finally {
    await setMenuItemPrice(page, 'Club Personal', '2.50');

    await page.goto('/menu');
    await expect(
      page.locator('.item').filter({ hasText: 'Club Personal' }).locator('.price')
    ).toHaveText('$2.50');
  }
});
