# Marea Alta — Frontend

Svelte 5 + Vite site for Marea Alta Surf Bar. Mobile-first, English/Spanish, no API keys needed. Three documents: the homepage, the standalone drinks menu at `/menu` and the news page at `/news`.

## Commands

```bash
npm install
npm run dev       # Start dev server at http://localhost:5173
npm run build     # Build for production → outputs dist/ (index.html, menu.html, news.html)
npm run preview   # Preview the production build locally
npm test          # Run the test suite once
npm run test:watch
npm run budget    # Fail if the gzipped JS/CSS build exceeds its budget
npm run lint      # svelte-check, warnings fail (the CI gate)
npm run check     # svelte-check, errors only (local convenience)
```

## Tests

Vitest with jsdom. The suite covers:

- `src/lib/api.test.js` — the language-fallback and time-formatting helpers, plus
  the bar's clock and the closed-day helpers.
- `src/lib/load.test.js` — the server-rendered payload is used once, then the API
  takes over for the hourly refresh; closures that have passed are dropped from
  both the seed and a stale cache; the menu rides along in the same payload and
  survives the offline fallback.
- `src/lib/menu.test.js` — `Menu.svelte` renders prices, promos and ingredients,
  falls back to English, and says nothing at all while loading.
- `src/lib/news.test.js` — `Blog.svelte` renders posts and the empty state, and
  `BlogPost.svelte` splits the body into paragraphs, switches language and shows
  an uploaded image.
- `src/lib/surf.test.js` — `Surf.svelte` reads the report from `/api/surf` (never
  a third party), renders the waves, tide turns, sun and wind, and shows its
  retry state when the API fails.
- `src/lib/publicI18n.test.js` — the labels the backend renders are the same
  strings this site shows, so a rename cannot silently leave the two disagreeing.
- `src/main.test.js` — all three entry points replace the server-rendered block on
  mount instead of stacking on it.
- `src/App.test.js` — renders the real component with a mocked `fetch` and
  asserts the schedule and the menu both switch language **without a remount**,
  and that a closure dated today hides tonight's party and the opening-hours line.

`src/App.test.js` is a deliberate regression guard. The week list once called
`pick()` through local wrapper functions, which hid `lang` from Svelte's
compiler dependency graph, so switching language left English on screen until a
page refresh. Keep `lang` passed as a literal argument in template expressions
— do not reintroduce the wrappers.

## Editing the Site

- **All wording:** `src/content/en.js` (English) and `src/content/es.js` (Spanish). Same structure in both.
  Missing Spanish keys fall back to English. `{full}`, `{town}`, `{year}` are filled in automatically.
- **Party schedule, hours, closed days, drinks menu:** *not* in this codebase. They are managed in the admin panel
  (`../backend`), fetched from `/api/*`, and rendered into the HTML by the backend. Do not hardcode
  schedule or menu values here.
- **Names, map link, social links:** `src/lib/data.js`.
- **Add a language:** copy `en.js` to `src/content/xx.js`, translate it, add it to `LANGS` in `src/lib/i18n.js`.
  The backend keeps its own copy of the handful of labels the server-rendered schedule uses
  (`../backend/app/public_i18n.py`) — `src/lib/publicI18n.test.js` fails if the two drift apart.
- The visitor's language choice is remembered; first visit follows the browser language.

## Three Documents

`npm run build` emits three HTML files, declared in `vite.config.js`:

| Entry | Route | Component |
|---|---|---|
| `index.html` → `src/main.js` | `/` | `App.svelte` — hero, surf, schedule, **menu**, visit |
| `menu.html` → `src/menu-main.js` | `/menu` | `MenuPage.svelte` — the menu alone, for sharing and indexing |
| `news.html` → `src/news-main.js` | `/news`, `/news/<slug>` | `NewsPage.svelte` — the post list and one article |

The homepage and `/menu` render the same `Menu.svelte`, so the drinks cannot
drift between them. `NewsPage` switches between `Blog.svelte` and
`BlogPost.svelte` from the path, so both news routes share one bundle. Modules
used by more than one document land in shared chunks.

The backend serves `/menu` and the two news routes by rendering `dist/menu.html`
and `dist/news.html` (`../backend/app/main.py`), so the content is in the HTML a
crawler sees. Proxy `/menu` and `/news` to the backend in nginx for the same
reason you proxy `/`.

## Schedule and Menu Data Flow

The first paint does not fetch anything. The backend renders the schedule and the menu into
`dist/index.html` at request time (see `../backend/app/ssr.py`) and hands the same payload to the
page as `window.__MAREA_ALTA_DATA__`. So a crawler sees the hours, party titles and prices in plain
HTML, and a visitor sees them immediately instead of a loading state.

That block lives in `#app` and is replaced when the app mounts:

- `src/main.js` and `src/menu-main.js` empty `#app` first, because Svelte's `mount()` **appends** — without the clear,
  the server-rendered copy and the live app both render and every visitor sees the schedule twice.
  `src/main.test.js` guards both.
- `src/lib/api.js#load()` uses the embedded payload for that first load only. Everything after it —
  the hourly refresh and the **Refresh** button — calls the API (`/api/schedule`, `/api/closed-days`,
  `/api/menu`), so an admin edit still appears without a reload.

The API returns **both languages** for every string, so:

- `pick(day, lang, 'title')` returns the visitor's language, falling back to
  English when that translation is blank. A partially-translated schedule still
  renders.
- Switching language re-renders from the already-fetched payload — no extra
  request.
- `formatHours()` renders 24-hour `HH:MM` values as 12-hour times per locale.
- `formatPrice()` renders a stored price — `"2.50"` → `$2.50` — and nothing at
  all for a drink that has not been priced yet. It mirrors `format_price()` in
  `ssr.py`; both have a test, because the crawler-visible HTML and the page must
  not disagree about what something costs.
- `barToday()` returns the day and the date **at the bar**, not where the visitor
  is. It mirrors `ssr.bar_today()`, and the two must agree: the schedule is keyed
  to Montañita's calendar, so a visitor in another timezone must not shift it.

## The Drinks Menu

`Menu.svelte` is presentational: it takes the categories from `load()` and renders
them. Prices, descriptions, ingredients and promos all come from the database via
`GET /api/menu`, and the admin panel at `/admin/menu` is where they are written.

- It is used twice — once on the homepage, once on `/menu` — so nothing about the
  drinks is hardcoded and the two pages cannot drift.
- While the menu is still loading it renders **nothing**, not the empty state:
  "the menu is being updated" is a lie for the second a fetch takes.
- An empty category never reaches the frontend — `load_menu()` drops them from
  the public read — so the bar can seed "Wine" and "Liquor" and fill them in
  later without a bare heading appearing on the site.

A day can be shut three ways, and `App.svelte` merges all three into one
`closedToday` flag:

- the weekday's own `is_closed` flag,
- a title of exactly "Closed" / "Cerrado" (kept for older rows where the hours and
  the title disagree), and
- a **closure dated today** in `closedDays` — a public holiday or a private
  booking, which the weekly schedule knows nothing about.

That flag hides the Tonight card, replaces tonight's party in the week list with
the closed label, and stops the Visit section claiming the bar is "open daily,
afternoon until late" on a day it is shut. Getting this wrong is what made a
closed holiday still advertise tonight's party.

Closures are also filtered **client-side** by `upcomingClosedDays()`, because
`GET /api/closed-days` filters to today-and-later but the `localStorage` cache and
the server-rendered seed both outlive the date they were fetched on.

Resilience and freshness:

- On success the response is cached in `localStorage`, including the embedded payload.
- If the backend is unreachable, the cached copy is used and the visitor sees a
  "showing cached data" notice instead of an empty schedule.
- Refreshed hourly, plus a manual **Refresh** button.

In development, `vite.config.js` proxies `/api` and `/admin` to
`http://localhost:8000`, so run the backend alongside this dev server. The dev server serves
`index.html` itself and does **not** run the server-side rendering, so the schedule and menu blocks are
absent locally — the SPA renders them from `/api/*` as it always has.

## Surf Widget

`src/lib/Surf.svelte` reads `GET /api/surf` from this origin. The backend calls
the free Open-Meteo marine + forecast APIs, shapes the result and caches it for
fifteen minutes (`../backend/app/surf.py`), so the visitor's phone never talks to
a third party and Open-Meteo sees one request per cache window rather than one
per page load. Coordinates for Montañita live in that module.

## Fonts and performance

The two typefaces (Bricolage Grotesque and Figtree) are self-hosted latin
subsets in `public/fonts/`, declared in `src/fonts.css` and preloaded from each
document's `<head>`. There are no Google Fonts requests, which is why the CSP no
longer allows any external origin. Fonts are cached by the service worker.

`npm run budget` gzips `dist/assets/` and fails above 80 KB of JavaScript, 16 KB
of CSS or a 40 KB single chunk. CI runs it after the build. Images that come from
the blog, gallery and calendar use `loading="lazy" decoding="async"`; the news
and blog images also carry intrinsic `width`/`height` so they cannot shift the
layout.

## Deployment

Run `npm run build` to produce `dist/` — `index.html`, `menu.html` and `news.html`. The backend serves
that directory from the same origin in production (see `../backend/README.md`), and renders `/`,
`/menu`, `/news` and `/news/<slug>` rather than serving those files straight off disk.

**nginx must proxy `/`, `/menu` and `/news` to the backend, not serve the files itself** — serving
them directly bypasses the rendering and the site goes back to being invisible to crawlers. Hashed
assets under `/assets/` and the self-hosted fonts under `/fonts/` can still be served by nginx
directly, with a long cache lifetime; see `../docs/deployment.md` for the gzip and cache block.

### SEO files

`public/robots.txt` is copied into `dist/` by Vite and served by the backend's static mount; it
disallows the admin panel and advertises the public documents. `public/sitemap.xml` is the fallback
copy the backend shadows with a dynamic route (`ssr.render_sitemap`), which lists published news
posts without a rebuild.

Each HTML entry point carries a canonical URL on the apex domain:

- `index.html` → `https://mareaaltabar.com/`
- `menu.html` → `https://mareaaltabar.com/menu`
- `news.html` → `https://mareaaltabar.com/news` (the backend rewrites this per article)

`src/seo.test.js` checks the files. If production moves to `www`, update the canonical tags and the
files in `public/`.
