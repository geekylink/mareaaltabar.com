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
  },
  // Vitest must load Svelte's client build, not the SSR build, or `mount()`
  // is unavailable. Without this, App.svelte cannot be mounted in tests.
  resolve: {
    conditions: ['browser'],
  },
});