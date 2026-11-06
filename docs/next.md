# Next work — implementable in this environment

This file tracks the remaining backlog items that can be built and tested on the
current machine (no Docker, VPS, external accounts, or missing business data).
It is updated after every completed ticket.

Source of truth for the full backlog: [`readme-tickets.md`](readme-tickets.md).
For everything that is **not** done and needs you — deploy, credentials, real
content, unrun checks — see [`../STILL_NEEDED.md`](../STILL_NEEDED.md).

## Completed in this batch

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
| 26 | Live music calendar | After #53: calendar over dated events. |
| 27 | “Perfect Drink” quiz | Frontend quiz resolving against `/api/menu`. |
| 29 | Referral program | After #21: codes and rewards on the loyalty table. |
| 32 | Dark mode toggle | CSS variables, toggle, persisted preference. |
| 33 | Accessibility pass | Public site and admin panel audit/fixes. |
| 34 | Performance optimizations | App-side: server-side surf proxy/cache, lazy loading, font preload. nginx caching is deploy-only. |
| 35 | Expanded automated testing | Playwright E2E + coverage; backend concurrency test already exists. |
| 36 | CI/CD rebuild (CI portion) | Rewrite workflow from `frontend/`, add PR CI and lint/check scripts. Deploy job needs VPS secrets. |
| 51 | Submission notification (fallback) | Shared inbox/unread count satisfies the useful half; email/WhatsApp needs a provider. |
| 56 | CSV export / import | Admin export/import with per-row validation. |

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
- **#24 Blog / news** — engine can be built; needs a committed writer.
- **#51 Full notification** — needs SMTP/WhatsApp credentials and destination.
- **#34 nginx caching** — needs the production server from #41.
- **#36 Deploy job** — needs VPS host, SSH key and deployment secrets.

## Not implementable on this machine

- **#41** Deploy to a production VPS — no VPS/nginx/systemd/TLS here.
- **#47** Google Business Profile — external, non-code.
- **#40** CDN — DNS/Cloudflare configuration.
- **#37** Sentry — external project/DSN.
- **#4** Analytics — external account and site ID.
- **#13** Instagram feed — third-party widget/account token.
- **#5 / #6 / #2** — blocked on the real phone number and street address.

## Next up

1. **#21** Loyalty program — buildable, but only useful once the owner decides
   punches, rewards and expiry.
2. **#26** Live music calendar — a calendar view over the dated events (#53).
3. **#27** “Perfect Drink” quiz — frontend-only, resolving against `/api/menu`.
