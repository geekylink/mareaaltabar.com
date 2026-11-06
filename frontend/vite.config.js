import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  build: {
    rollupOptions: {
      // Three documents: the homepage, the standalone menu and the news/blog.
      // Vite emits `dist/index.html`, `dist/menu.html` and `dist/news.html`, and
      // the backend renders a route for each (`/`, `/menu`, `/news` and
      // `/news/<slug>`, see backend/app/main.py). Modules shared by more than
      // one — the API client, the i18n store — land in shared chunks rather than
      // being duplicated.
      input: {
        main: resolve(import.meta.dirname, 'index.html'),
        menu: resolve(import.meta.dirname, 'menu.html'),
        news: resolve(import.meta.dirname, 'news.html'),
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