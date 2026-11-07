import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte({ hot: false })],
  test: {
    environment: 'jsdom',
    globals: true,
    pool: 'threads',
    include: ['src/**/*.test.js'],
    setupFiles: ['./src/test-setup.js'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{js,svelte}'],
      // Translation copy and the jsdom shims are data/plumbing, not behaviour.
      exclude: ['src/content/**', 'src/test-setup.js'],
      reporter: ['text', 'lcov'],
      // Set just below the measured baseline (95.2 / 94.5 / 95.5 / 72.5) so the
      // gate is honest today and ratchets up as tests are added. Raise these
      // when a change covers a gap; never lower them to make a red build green.
      thresholds: {
        lines: 93,
        statements: 92,
        functions: 93,
        branches: 70,
      },
    },
  },
  // Vitest must load Svelte's client build, not the SSR build, or `mount()`
  // is unavailable. Without this, App.svelte cannot be mounted in tests.
  resolve: {
    conditions: ['browser'],
  },
});