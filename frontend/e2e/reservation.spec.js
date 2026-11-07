import { test, expect } from '@playwright/test';
import { login } from './helpers.js';

test('a reservation is submitted and appears in the admin queue', async ({ page }) => {
  await page.goto('/');

  const form = page.locator('#reservation');
  const date = form.locator('input[type="date"]');
  // The bar's own today, from the form's own bound. Filling the server's UTC
  // date can be yesterday or tomorrow on the Ecuador coast.
  await date.fill(await date.getAttribute('min'));
  await form.locator('input[type="number"]').fill('3');
  await form.locator('input[autocomplete="name"]').fill('E2E Guest');
  await form.locator('input[autocomplete="email"]').fill('e2e@example.com');
  await form.getByRole('button', { name: 'Request a table' }).click();

  await expect(form.getByRole('status')).toHaveText(
    'Request received. We will confirm with you soon.'
  );

  await login(page);
  await page.goto('/admin/reservations');
  await expect(page.locator('#reservations').getByText('E2E Guest')).toBeVisible();
});
