# Marea Alta — Frontend

Svelte 5 + Vite static site for Marea Alta Surf Bar. Mobile-first, English/Spanish, no API keys needed.

## Commands

```bash
npm install
npm run dev       # Start dev server at http://localhost:5173
npm run build     # Build for production → outputs dist/
npm run preview   # Preview the production build locally
npm test          # Run the test suite once
npm run test:watch
```

## Tests

Vitest with jsdom. Five files:

- `src/lib/api.test.js` — the language-fallback and time-formatting helpers.
- `src/lib/load.test.js` — the server-rendered payload is used once, then the API
  takes over for the hourly refresh.
- `src/lib/publicI18n.test.js` — the labels the backend renders are the same
  strings this site shows, so a rename cannot silently leave the two disagreeing.
- `src/main.test.js` — the app replaces the server-rendered block on mount.
- `src/App.test.js` — renders the real component with a mocked `fetch` and
  asserts the schedule switches language **without a remount**.

`src/App.test.js` is a deliberate regression guard. The week list once called
`pick()` through local wrapper functions, which hid `lang` from Svelte's
compiler dependency graph, so switching language left English on screen until a
page refresh. Keep `lang` passed as a literal argument in template expressions
— do not reintroduce the wrappers.

## Editing the Site

- **All wording:** `src/content/en.js` (English) and `src/content/es.js` (Spanish). Same structure in both.
  Missing Spanish keys fall back to English. `{full}`, `{town}`, `{year}` are filled in automatically.
- **Party schedule, hours, closed days:** *not* in this codebase. They are managed in the admin panel
  (`../backend`), fetched from `/api/*`, and rendered into the HTML by the backend. Do not hardcode
  schedule values here.
- **Names, map link, social links:** `src/lib/data.js`.
- **Add a language:** copy `en.js` to `src/content/xx.js`, translate it, add it to `LANGS` in `src/lib/i18n.js`.
  The backend keeps its own copy of the handful of labels the server-rendered schedule uses
  (`../backend/app/public_i18n.py`) — `src/lib/publicI18n.test.js` fails if the two drift apart.
- The visitor's language choice is remembered; first visit follows the browser language.

## Schedule Data Flow

The first paint does not fetch anything. The backend renders the schedule into
`dist/index.html` at request time (see `../backend/app/ssr.py`) and hands the same payload to the
page as `window.__MAREA_ALTA_DATA__`. So a crawler sees the hours and party titles in plain HTML, and
a visitor sees the schedule immediately instead of a loading state.

That block lives in `#app` and is replaced when the app mounts:

- `src/main.js` empties `#app` first, because Svelte's `mount()` **appends** — without the clear,
  the server-rendered copy and the live app both render and every visitor sees the schedule twice.
  `src/main.test.js` guards this.
- `src/lib/api.js#load()` uses the embedded payload for that first load only. Everything after it —
  the hourly refresh and the **Refresh** button — calls the API, so an admin edit still appears
  without a reload.

The API returns **both languages** for every string, so:

- `pick(day, lang, 'title')` returns the visitor's language, falling back to
  English when that translation is blank. A partially-translated schedule still
  renders.
- Switching language re-renders from the already-fetched payload — no extra
  request.
- `formatHours()` renders 24-hour `HH:MM` values as 12-hour times per locale.

Resilience and freshness:

- On success the response is cached in `localStorage`, including the embedded payload.
- If the backend is unreachable, the cached copy is used and the visitor sees a
  "showing cached data" notice instead of an empty schedule.
- Refreshed hourly, plus a manual **Refresh** button.

In development, `vite.config.js` proxies `/api` and `/admin` to
`http://localhost:8000`, so run the backend alongside this dev server. The dev server serves
`index.html` itself and does **not** run the server-side rendering, so the schedule block is absent
locally — the SPA renders it from `/api/*` as it always has.

## Surf Widget

`src/lib/Surf.svelte` calls the free Open-Meteo marine + forecast APIs from the visitor's browser.
Coordinates for Montañita are at the top of the file.

## Deployment

Run `npm run build` to produce `dist/`. The backend serves that directory from
the same origin in production (see `../backend/README.md`), and renders `/` rather than serving
`dist/index.html` straight off disk.

**nginx must proxy `/` to the backend, not serve `dist/index.html` itself** — serving the file directly
bypasses the rendering and the site goes back to being invisible to crawlers. Hashed assets under
`/assets/` can still be served by nginx directly.
