# Marea Alta — Frontend

Svelte 5 + Vite static site for Marea Alta Surf Bar. Mobile-first, English/Spanish, no API keys needed.

## Commands

```bash
npm install       # Install dependencies
npm run dev       # Start dev server at http://localhost:5173
npm run build     # Build for production → outputs dist/
npm run preview   # Preview the production build locally
```

## Editing the Site

- **All wording:** `src/content/en.js` (English) and `src/content/es.js` (Spanish). Same structure in both.
  Missing Spanish keys fall back to English. `{full}`, `{town}`, `{year}` are filled in automatically.
- **Party schedule, hours, closed days:** *not* in this codebase. They are managed in the admin panel
  (`../backend`) and fetched at runtime from `/api/*`. Do not hardcode schedule values here.
- **Names, map link, social links:** `src/lib/data.js`.
- **Add a language:** copy `en.js` to `src/content/xx.js`, translate it, add it to `LANGS` in `src/lib/i18n.js`.
- The visitor's language choice is remembered; first visit follows the browser language.

## Schedule Data Flow

`src/lib/api.js` fetches `/api/events`, `/api/hours`, and `/api/closed-days`:

- On success the response is cached in `localStorage`.
- If the backend is unreachable, the cached copy is used and the visitor sees a
  "showing cached data" notice instead of an empty schedule.
- The schedule is fetched on page load, then refreshed hourly, plus a manual
  **Refresh** button.

In development, `vite.config.js` proxies `/api` and `/admin` to
`http://localhost:8000`, so run the backend alongside this dev server.

## Surf Widget

`src/lib/Surf.svelte` calls the free Open-Meteo marine + forecast APIs from the visitor's browser.
Coordinates for Montañita are at the top of the file.

## Deployment

Run `npm run build` to produce `dist/`. The backend serves that directory from
the same origin in production (see `../backend/README.md`).
