import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  build: {
    rollupOptions: {
      // Two documents: the homepage and the standalone menu route. Vite emits
      // `dist/index.html` and `dist/menu.html`, and the backend renders a route
      // for each (`/` and `/menu`, see backend/app/main.py). Modules used by both
      // — the API client, the i18n store, the menu component — land in shared
      // chunks rather than being duplicated.
      input: {
        main: resolve(import.meta.dirname, 'index.html'),
        menu: resolve(import.meta.dirname, 'menu.html'),
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/admin': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});