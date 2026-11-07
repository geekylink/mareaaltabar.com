# Next work — implementable in this environment

This file tracks the remaining backlog items that can be built and tested on the
current machine (no Docker, VPS, external accounts, or missing business data).
It is updated after every completed ticket.

Source of truth for the full backlog: [`readme-tickets.md`](readme-tickets.md).
For everything that is **not** done and needs you — deploy, credentials, real
content, unrun checks — see [`../STILL_NEEDED.md`](../STILL_NEEDED.md).

## Completed in this batch

- **#34 Performance optimizations** — `GET /api/surf` proxies Open-Meteo on the
  server and caches the shaped report for fifteen minutes, with stale-on-error
  fallback; `Surf.svelte` makes one same-origin read instead of two third-party
  calls. Both typefaces are self-hosted latin variable subsets, preloaded from
  every document and no longer requested from Google Fonts, so the CSP allows
  only `'self'`. Images decode asynchronously, the service worker caches
  `/api/surf` and `/fonts/`, and `npm run budget` (run in CI) enforces gzipped
  JS/CSS/chunk limits. The nginx gzip/cache half and a measured Lighthouse run
  need the production server. Tests: `backend/tests/test_surf.py`,
  `frontend/src/lib/surf.test.js`.
- **#33 Accessibility pass** — every public page starts with a translated skip
  link to one `<main id="main">` landmark, and the standalone menu page now has
  a visible `<h1>`. The calendar is a labelled table with `aria-current="date"`
  on today, interactive controls declare `type="button"`, the surf error and
  critical notices announce themselves, and the menu keeps an accessible name
  when its heading is hidden. Focus rings were restored over component-level
  `outline: none` on the public forms and every admin field, faint admin text
  moved to `#5f5f5f` (public `--text-faint` to `#6f665a`) to clear WCAG AA, and
  admin status/error slots are now live regions. A real assistive-technology
  pass remains on `STILL_NEEDED.md`. Tests: `frontend/src/App.test.js`, plus the
  existing component suites.
- **#36 CI/CD rebuild** — `.github/workflows/ci.yml` runs the backend
  (`ruff` + `pytest`) and frontend (`svelte-check` + Vitest + build) on every
  pull request and push to `main`; `.github/workflows/deploy.yml` waits for
  that run to succeed, builds `frontend/dist`, rsyncs the code and build over
  SSH, and restarts the service. The deploy job is gated on `DEPLOY_ENABLED` so
  it stays skipped until #41 provides the VPS and secrets. Tests: the workflows
  themselves; `backend/ruff.toml`, `frontend/svelte.config.js`.
- **#24 News / blog** — a `blog_posts` table with its own slug, bilingual
  title/excerpt/body, optional image, publication date and active flag.
  `/news` lists published posts and `/news/<slug>` renders one article from the
  same Vite entry; the backend injects both into the HTML, rewrites the head
  metadata per article and emits `BlogPosting` JSON-LD. `/admin/blog` writes,
  schedules, edits and deletes posts, and `/sitemap.xml` is now dynamic so a new
  post appears without a rebuild. One bilingual launch post is seeded only into
  an empty table. Tests: `backend/tests/test_blog.py`,
  `frontend/src/lib/news.test.js`.
- **#32 Dark mode toggle** — the public site now has a light/dark theme switch
  in the shared header. A saved choice lives in `localStorage` under `theme`,
  and a first-time visitor follows `prefers-color-scheme`. The backend injects a
  nonce-protected head script so the chosen theme is on `<html>` before the
  first paint; the Svelte store keeps it in sync afterwards. Colours moved to
  semantic CSS variables in `app.css`, with a dark override and a system-dark
  fallback for JavaScript-disabled visitors. Tests: `theme.test.js`,
  `nav.test.js`, `backend/tests/test_ssr.py`.
- **#56 CSV export / import** — `/admin/data` downloads seven tables as CSV:
  menu categories, items and promos, content sections and items, special events
  and reservations. Import is all-or-nothing: every row is validated with the
  same Pydantic rules as the admin forms, and one bad row changes nothing. Rows
  update by id (or slug for categories/sections); a blank id creates; nothing is
  deleted. Imports are audited and a new drink of the day clears the others.
  Reservations are export-only. Tests: `backend/tests/test_csv_data.py`.
- **#27 “Perfect Drink” quiz** — a three-question frontend quiz (`mood`, `taste`,
  `night`) scores the live `/api/menu` categories and items, so a removed or
  unavailable drink can never be recommended. Cigarettes are excluded. The result
  shows name, category, price, description and ingredients, can be restarted, and
  uses the Web Share API with a clipboard fallback. Nothing is persisted. Rules
  live in `frontend/src/lib/quizRules.js`; copy is bilingual. Tests:
  `frontend/src/lib/quizRules.test.js`, `frontend/src/lib/quiz.test.js`.
- **#26 Live music calendar** — a month grid over the dated events (#53)
  replaces the flat special-events list on the homepage. It opens on the soonest
  event's month, marks event days, pages between months and shows the selected
  day's title, time, description, image and RSVP form. Artist names and genres
  use the event title and description; there is no Bandsintown sync or separate
  social-link field. Tests: `frontend/src/lib/calendar.test.js`.
- **#31 PWA support** — `/manifest.json` and a service worker make the site
  installable. The worker precaches the shell (`/`, `/menu` and an offline
  fallback), uses network-first for navigations and the five public API reads,
  cache-first for hashed assets and uploaded images, and never touches `/admin`
  or admin API reads. An `InstallPrompt.svelte` strip appears only when Chromium
  fires `beforeinstallprompt`; registration is production-only and runs from
  both entry points. Tests: `frontend/src/pwa.test.js`,
  `frontend/src/lib/installPrompt.test.js`.
- **#25 Event RSVPs** — free RSVPs attach to a dated event (#53), separate from
  table reservations. `POST /api/special-events/{id}/rsvp` accepts a name,
  contact, party of 1–20 and notes, with the same honeypot and per-IP limiter as
  the other public forms; hidden, past and unknown events return 404. Each event
  on the homepage has an expandable RSVP form. `/admin/rsvps` filters by event
  and shows both the RSVP count and the total number of people coming; the
  dashboard links to it. Deleting an event removes its guest list. Paid
  ticketing is deliberately left to Eventbrite/Ticket Tailor. Tests:
  `backend/tests/test_rsvp.py`, `frontend/src/lib/rsvp.test.js`.
- **#50 Image upload pipeline** — admin-only `POST /api/uploads` accepts JPEG,
  PNG, WebP and GIF up to 10 MB, verifies the bytes with Pillow, applies EXIF
  orientation, resizes to 1600 px and a 480 px thumbnail, and re-encodes both to
  WebP. Files live under `UPLOAD_DIR` (outside the database) and are served at
  `/uploads/<random>.webp` with an immutable cache header. `/admin/uploads`
  uploads, captions and deletes; every action is logged in the content area.
  Tests: `backend/tests/test_uploads.py`.
- **#16 Shared navigation** — one `Nav.svelte` now renders the header on `/` and
  `/menu`. The homepage links are in-page anchors; the menu page points back at
  `/#…`, drops the “Menu” item it is already on, and keeps the language selector.
  Tests: `nav.test.js`.
- **#10 Drink of the Day** — `menu_items.is_drink_of_day` is set from the menu
  admin page; write handlers clear every other row so only one drink is featured.
  The homepage hero renders `DrinkOfDay.svelte` from the already-loaded menu, so
  there is no extra request. Tests: `test_api_menu.py`, `drinkOfDay.test.js`.
- **#17 Generic content tables** — `content_sections` / `content_items` with
  bilingual title/body, optional price, image URL, date window, sort order and
  active flag. Public `GET /api/content` and `/api/content/{slug}` hide inactive,
  expired and empty sections; `/api/content/all` is the admin read. `/admin/content`
  edits sections and rows in place, and changes are logged in a fourth content tab
  on `/admin/logs`. Tests: `test_content.py`.
- **#12 Newsletter signup** — `subscribers` table, public `POST /api/newsletter`
  with explicit consent, honeypot, per-IP rate limiting and a duplicate-safe
  response, plus `/admin/subscribers` to unsubscribe/delete and export the active
  list as CSV. There is no delivery provider or double opt-in yet. Tests:
  `test_newsletter.py`, `newsletter.test.js`.
- **#14 Reservation requests** — `reservations` table and public
  `POST /api/reservations` (today to 90 days out, 1–20 guests, pending always).
  `/admin/reservations` filters, confirms, declines, resets and deletes; the
  dashboard shows a pending badge. No guest notification is sent — that is #51.
  Tests: `test_reservations.py`, `reservation.test.js`.

- **#3 Open Graph / social preview tags** — static `og:*` and Twitter card tags on
  `/` and `/menu`, plus generated 1200×630 preview images. Tests: `seo.test.js`.
- **#9 Favicon and app icons** — SVG, 16/32/180/192/512 PNGs and a multi-size
  `.ico`; the emoji data-URI favicon is gone from the site and every admin page.
  Tests: `seo.test.js`, `backend/tests/test_assets.py`.
- **#7 Happy hour / daily promos** — weekday, time (including overnight) and
  date windows on menu promos, plus an active switch. Public menu/API/SSR only
  publish live offers; the admin read keeps every offer with `is_live`, and the
  panel edits the window per promo. Tests: `test_api_menu.py`,
  `test_migrations.py`, `test_ssr.py`, `menu.test.js`.
- **#15 Contact form + shared admin inbox** — public `POST /api/contact` with a
  1,000-character message cap, tag/control-character stripping, a honeypot and
  per-IP rate limiting. Messages store IP and user agent and land in
  `/admin/inbox`, shared by every admin, with read/unread and delete. The
  dashboard shows an unread badge. Tests: `backend/tests/test_contact.py`,
  `frontend/src/lib/contact.test.js`.
- **#53 Dated / special events** — `special_events` table with date, bilingual
  title and description, optional time window (overnight supported), optional
  image URL and active switch. Public API and SSR render upcoming events
  alongside the weekly schedule; the admin read keeps past/hidden rows, and
  `/admin/events` adds, edits and deletes them. Tests:
  `backend/tests/test_special_events.py`, `App.test.js`, `api.test.js`.

## Remaining, ready to build here

| # | Ticket | Notes |
|---|--------|-------|
| 21 | Loyalty program | Punch-card table, admin counter/redeem, public signup/QR. Needs owner rules. |
| 29 | Referral program | After #21: codes and rewards on the loyalty table. |
| 35 | Expanded automated testing | Playwright E2E + coverage; backend concurrency test already exists. |
| 51 | Submission notification (fallback) | Shared inbox/unread count satisfies the useful half; email/WhatsApp needs a provider. |

## Buildable, but needs owner content/assets/credentials

- **#8 Photo gallery** — engine can be built; needs real photos (upload pipeline #50 is ready).
- **#30 Signature drinks** — `is_featured` + section; needs photos (upload pipeline #50 is ready).
- **#22 Birthday / package deals** — needs real package tiers and prices.
- **#23 Merch / store** — needs products, sizes/colours, photos.
- **#28 Photo contest / UGC** — needs photos, rules and consent wording.
- **#19 About Us** — needs the bar’s story and dates.
- **#20 Private events / group booking** — needs capacity, pricing and policy.
- **#18 Drink descriptions** — content only; admin already supports it.
- **#11 Food menu** — data entry only; needs the real menu.
- **#51 Full notification** — needs SMTP/WhatsApp credentials and destination.
- **#34 nginx gzip/cache and Lighthouse score** — the app-side work is shipped;
  the nginx block in `docs/deployment.md` and a measured mobile Lighthouse run
  need the production server from #41.
- **#36 Deploy job** — the workflow is shipped and gated on `DEPLOY_ENABLED`;
  activating it needs the VPS host, SSH key and deployment secrets from #41.

## Not implementable on this machine

- **#41** Deploy to a production VPS — no VPS/nginx/systemd/TLS here.
- **#47** Google Business Profile — external, non-code.
- **#40** CDN — DNS/Cloudflare configuration.
- **#37** Sentry — external project/DSN.
- **#4** Analytics — external account and site ID.
- **#13** Instagram feed — third-party widget/account token.
- **#5 / #6 / #2** — blocked on the real phone number and street address.

## Next up

1. **#30** Signature drinks — `is_featured` plus a "Drinks We're Known For"
   section.
2. **#35** Expanded automated testing — Playwright E2E + coverage; the backend
   concurrency test already exists.
3. **#19 / #8 / #20 / #22** — content surfaces that can be built now and filled
   when the owner supplies photos, story, package tiers and group policy.
