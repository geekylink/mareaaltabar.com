import { defineConfig, devices } from '@playwright/test';

// Real-browser coverage for the paths that cost money if they break: the menu
// and its prices, the language switch, an admin edit reaching the public page,
// and a reservation landing in the admin queue.
//
// Chromium is the CI browser: it is the engine every Android visitor uses and
// the cheapest one to install. Safari/WebKit, Firefox and real devices stay on
// the manual pre-launch checklist in STILL_NEEDED.md.
export default defineConfig({
  testDir: './e2e',
  outputDir: 'test-results',
  // One worker against one throwaway database. The admin-edit test changes a
  // price and restores it, but serial execution keeps every spec deterministic.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI
    ? [['github'], ['html', { open: 'never' }]]
    : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:8010',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    // Builds nothing: `npm run test:e2e` builds first, because FastAPI renders
    // `/` and `/menu` from frontend/dist.
    command: 'bash e2e/start-server.sh',
    url: 'http://127.0.0.1:8010/healthz',
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
