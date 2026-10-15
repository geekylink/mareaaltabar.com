# README-tickets.md

> **Companion to the Marea Alta Surf Bar website.** This document is the improvement backlog for the site. It was first written when Marea Alta was a static Svelte app with everything hardcoded in `src/lib/data.js`. The site now has a **FastAPI + SQLite backend**, a bilingual admin panel, and a public read API — so this list has been rebuilt around that reality.
>
> **What changed.** The original list assumed no backend. That made "add a CMS" and "add backups *if* you have a database" into large speculative projects. Both are now smaller and more concrete: the CMS is *this* database, and backups are a cron line. Meanwhile the backend introduced a class of work the original list never considered — deployment, database concurrency, secrets, and abuse of public write endpoints — which is why **Tier 0 now exists at all**.
>
> The business is still drinks. The original argument for putting the menu first holds, and ticket **#1** is the flagship.

**Legend**
- **Impact:** 🔴 Critical · 🟠 High · 🟡 Medium · ⚪ Low
- **Effort:** 🟢 S (<1 day) · 🟡 M (1–3 days) · 🔴 L (1+ week)

---

Project manager note:
* Finished tickets should be moved to "Completed Tickets" section and removed from "TO-DO"
* Ticket should be marked completed in "Summary Table"
* Cross out ticket number in "Suggested Sprint Order"

---

## How to read this list

**Ticket numbers are stable.** The original 40 keep the numbers they had, even though their priority and content have changed. New tickets continue from 41. This is deliberate: the tier a ticket sits in is now more meaningful than its number, and a ticket that moved from Tier 4 to Tier 0 should *look* like it moved.

**Each ticket lists the files it touches.** These are real paths in this repository, verified against the current tree. Where a ticket extends an existing pattern (menu → `events`/`hours`, admin page → `schedule.html`), the ticket says so, because following the existing pattern is most of the work.

---

## Table of Contents

- [Tier 0 — Ship It](#tier-0--ship-it)
  - [41. Deploy the backend to production (VPS)](#41-deploy-the-backend-to-production-vps)
  - [42. Fix closed-day handling on the public site](#42-fix-closed-day-handling-on-the-public-site)
  - [43. Harden SQLite for concurrent production writes](#43-harden-sqlite-for-concurrent-production-writes)
  - [44. Production environment & secrets runbook](#44-production-environment--secrets-runbook)
  - [36. CI/CD rebuild](#36-cicd-rebuild)
  - [38. Automated database backups & restore drill](#38-automated-database-backups--restore-drill)
  - [39. Uptime monitoring & health endpoint](#39-uptime-monitoring--health-endpoint)
  - [45. Security headers: HSTS & CSP](#45-security-headers-hsts--csp)
- [Tier 1 — Get Found](#tier-1--get-found)
  - [5. Add structured data (Schema.org LocalBusiness)](#5-add-structured-data-schemaorg-localbusiness)
  - [6. Display phone number and address prominently](#6-display-phone-number-and-address-prominently)
  - [2. Add WhatsApp floating button](#2-add-whatsapp-floating-button)
  - [47. Set up a Google Business Profile](#47-set-up-a-google-business-profile)
  - [3. Add Open Graph / social preview tags](#3-add-open-graph--social-preview-tags)
  - [4. Add analytics](#4-add-analytics)
  - [48. robots.txt, sitemap.xml & canonical URLs](#48-robotstxt-sitemapxml--canonical-urls)
  - [9. Add proper favicon and app icons](#9-add-proper-favicon-and-app-icons)
- [Tier 2 — Sell the Drinks](#tier-2--sell-the-drinks)
  - [1. Add a drinks menu page](#1-add-a-drinks-menu-page)
  - [17. Content tables for promos, packages & gallery](#17-content-tables-for-promos-packages--gallery)
  - [16. Create separate menu page (multi-page structure)](#16-create-separate-menu-page-multi-page-structure)
  - [49. Menu SEO (Menu schema & indexable menu route)](#49-menu-seo-menu-schema--indexable-menu-route)
  - [7. Add happy hour / daily promos section](#7-add-happy-hour--daily-promos-section)
  - [18. Add drink pricing and descriptions](#18-add-drink-pricing-and-descriptions)
  - [11. Add food menu section](#11-add-food-menu-section)
  - [30. Add "Drinks We're Known For" signature section](#30-add-drinks-were-known-for-signature-section)
  - [10. Add a "Drink of the Day" hero banner](#10-add-a-drink-of-the-day-hero-banner)
  - [22. Add birthday / package deals](#22-add-birthday--package-deals)
  - [19. Add "About Us" section](#19-add-about-us-section)
  - [20. Add private events / group booking info](#20-add-private-events--group-booking-info)
- [Tier 3 — Convert & Retain](#tier-3--convert--retain)
  - [15. Add contact form](#15-add-contact-form)
  - [12. Add email capture / newsletter signup](#12-add-email-capture--newsletter-signup)
  - [51. Notify the bar when a submission arrives](#51-notify-the-bar-when-a-submission-arrives)
  - [14. Add reservation / table booking system](#14-add-reservation--table-booking-system)
  - [52. Emergency notice banner](#52-emergency-notice-banner)
  - [50. Image upload pipeline](#50-image-upload-pipeline)
  - [8. Add photo gallery](#8-add-photo-gallery)
  - [13. Embed Instagram feed](#13-embed-instagram-feed)
  - [53. Dated / special events](#53-dated--special-events)
  - [25. Add event ticketing / RSVP](#25-add-event-ticketing--rsvp)
  - [26. Add live music calendar](#26-add-live-music-calendar)
- [Tier 4 — Grow the Business](#tier-4--grow-the-business)
  - [21. Add loyalty program](#21-add-loyalty-program)
  - [24. Add blog / news section](#24-add-blog--news-section)
  - [28. Add user-generated content (photo contest)](#28-add-user-generated-content-photo-contest)
  - [29. Add referral program](#29-add-referral-program)
  - [27. Add "Perfect Drink" quiz / recommendation](#27-add-perfect-drink-quiz--recommendation)
  - [23. Add merch / store section](#23-add-merch--store-section)
- [Tier 5 — Operate & Polish](#tier-5--operate--polish)
  - [35. Expand automated testing](#35-expand-automated-testing)
  - [37. Add error tracking (Sentry)](#37-add-error-tracking-sentry)
  - [54. Admin password change & second admin](#54-admin-password-change--second-admin)
  - [55. Audit log of admin edits](#55-audit-log-of-admin-edits)
  - [33. Accessibility pass](#33-accessibility-pass)
  - [34. Performance optimizations](#34-performance-optimizations)
  - [31. Add PWA support](#31-add-pwa-support)
  - [56. Data export / import (CSV)](#56-data-export--import-csv)
  - [40. Add CDN in front of the server](#40-add-cdn-in-front-of-the-server)
  - [32. Add dark mode toggle](#32-add-dark-mode-toggle)
- [Summary Table](#summary-table)
- [Suggested Sprint Order](#suggested-sprint-order)
- [Completed Tickets](#completed-tickets)

---

# TO-DO

## Tier 0 — Ship It

*The backend exists but has never been deployed. `.github/workflows/deploy.yml` runs `npm ci` at the repository root, where there is no `package.json` — it has failed on every push since the `frontend/` restructure. Nothing in Tiers 1–5 is worth anything until the site is actually serving.*

### 41. Deploy the backend to production (VPS)
**Impact:** 🔴 · **Effort:** 🟡 · **Category:** DevOps

Provision a VPS, install Python 3.12, and run the backend as a managed service. `backend/app/main.py` already mounts `frontend/dist` as a static mount registered *last*, so FastAPI can serve the whole site from one origin with no CORS — that design is the reason this ticket is straightforward. Add a systemd unit (survives reboot, restarts on crash, `--reload` off in production), and an nginx reverse proxy in front of it for TLS, static caching, and gzip. Terminate TLS with Let's Encrypt and redirect HTTP to HTTPS — ticket #45 and the `Secure` cookie flag both depend on it. Set `ENVIRONMENT=production` so `/docs` is disabled and cookies require HTTPS. Document the deploy in `backend/README.md`.

**Since #46:** nginx must proxy `/` to uvicorn rather than serving `dist/index.html` itself — serving the file directly bypasses the server-rendered schedule and puts the hours back out of reach of crawlers. `/assets/` can still be served from disk with a long cache lifetime.

**Files:** new `deploy/marea-alta.service`, new `deploy/nginx.conf`, `backend/README.md` (deploy section), `backend/.env`

---

### 42. Fix closed-day handling on the public site
**Impact:** 🔴 · **Effort:** 🟢 · **Category:** Functionality

Two real bugs, both created by the frontend not fully honouring backend data. **First:** `App.svelte` computes `tonightClosed` from the weekday `is_closed` flag and a title regex, but never checks `closedDays` for today's date — so a public holiday the bar explicitly closed for still renders "Tonight: <party name>" in the highlight card, plus an "open until late" hours line in the Visit section. **Second:** `GET /api/closed-days` returns every row with no date filter, so closures render on the site forever; `ClosedDayCreate` blocks *creating* past dates but nothing stops them being *displayed* after they pass. Fix by filtering the API to today-and-later, and by deriving a `closedToday` flag in the frontend that merges both sources into the hero, the Tonight card, and the week row.

**Files:** `backend/app/routers/api.py` (filter closed days), `backend/app/schemas.py` (if a new field is needed), `frontend/src/App.svelte`, `frontend/src/lib/api.js`, `backend/tests/test_api_closed_days.py`

---

### 43. Harden SQLite for concurrent production writes
**Impact:** 🔴 · **Effort:** 🟢 · **Category:** DevOps

`backend/app/database.py` creates a plain SQLite engine with no WAL mode and no `busy_timeout`, while `backend/README.md` tells operators to run `uvicorn --workers 4`. Four worker processes writing one database file will intermittently throw `database is locked`, and admin saves during a busy Friday are exactly when that happens. Either enable WAL plus a busy timeout on connect (letting readers and a writer coexist), or accept the constraint and run a single worker behind nginx — which is genuinely fine at this traffic level and is the lower-risk choice. Whichever is picked, the README must stop advertising `--workers 4` for SQLite. Add a test that performs concurrent writes through separate sessions.

**Files:** `backend/app/database.py` (connect event / `connect_args`), `backend/README.md`, new `backend/tests/test_concurrency.py`

---

### 44. Production environment & secrets runbook
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Operations

There is no documented production environment, and the config is actively misleading. `SECRET_KEY` is declared in `backend/app/config.py` and documented in `backend/README.md` as "random secret for session signing", but **nothing reads it** — `app/auth.py` stores cryptographically random tokens in the `sessions` table instead. It is dead config that will make whoever does the deploy hunt for a setting that does nothing. Remove it and correct the README. Then write down the real production `.env`: `ENVIRONMENT`, `DATABASE_PATH` (an absolute path outside the repo), `COOKIE_SECURE=true`, `SESSION_TTL_HOURS`, and the rate-limit values. Note that `.env` and `backend/data/` are gitignored, so nothing sensitive or durable is in version control.

**Files:** `backend/app/config.py` (remove `SECRET_KEY`), `backend/README.md` (config table), new `docs/deployment.md`

---

### 36. CI/CD rebuild
**Impact:** 🔴 · **Effort:** 🟡 · **Category:** DevOps

The current workflow is broken rather than merely basic. It runs `npm ci` and `npm run build` at the repository root, where there is no `package.json`, then uploads `./dist` — a path that stopped existing when the project moved into `frontend/`. It also targets GitHub Pages, which can never host the API. Replace it with a pipeline that matches the architecture chosen in #41: build the frontend in `frontend/`, run both test suites (see #35), then deploy to the VPS over SSH. Add lint and type-check gates — `svelte-check` on the frontend, `ruff` on the backend — so a broken build cannot reach the server. Add `.github/workflows/ci.yml` for pull requests that runs checks without deploying.

**Files:** `.github/workflows/deploy.yml` (rewrite), new `.github/workflows/ci.yml`, `frontend/package.json` (add `lint`, `check` scripts), `backend/requirements.txt` (add `ruff`)

---

### 38. Automated database backups & restore drill
**Impact:** 🔴 · **Effort:** 🟢 · **Category:** DevOps

This ticket used to be conditional — "if using a CMS or database, implement automated backups" — because a static site had nothing to lose. That condition is now always true, and the risk is live: `backend/.gitignore` excludes `backend/data/`, so the SQLite file containing the schedule, hours, and closures exists on exactly one disk with no copy. Use `sqlite3 .backup` (not `cp`, which can capture a torn write) on a nightly cron, retain 14–30 days, and ship copies off the VPS. Then **actually restore from a backup into a scratch directory and confirm the schedule comes back** — an untested backup is not a backup. Document both halves in the runbook from #44.

**Files:** new `scripts/backup.sh`, new `docs/deployment.md` (restore section), `.gitignore`

---

### 39. Uptime monitoring & health endpoint
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** DevOps

Monitoring a two-tier app by pinging the homepage will miss most failures — the static mount can serve a perfectly good page while the API is returning 500s and the schedule is silently blank. Add `GET /healthz` that checks database connectivity and returns 200/503, and point an external monitor (UptimeRobot or Better Stack, free tier) at it rather than at `/`. A dead schedule on a Friday night costs real money. The existing GitHub Actions cron is not sufficient because it only runs while someone is committing.

**Files:** new route in `backend/app/routers/api.py`, new `backend/tests/test_health.py`, `backend/README.md`

---

### 45. Security headers: HSTS & CSP
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Security

`app/main.py` sets three headers — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` — which is a good start. Two are now missing that matter more than they used to. **HSTS** should be added once #41's TLS is live, so browsers stop offering to load the admin panel over plaintext. **Content-Security-Policy** was optional for a static site but is worth real attention now: the admin panel holds a session cookie and posts CSRF-protected forms, so a CSP blocks a whole class of injection. Build it incrementally with `default-src 'self'` and add exceptions for the Google Fonts stylesheet and the Open-Meteo endpoints that `Surf.svelte` calls. Add `Permissions-Policy` while in there.

**Files:** `backend/app/main.py` (middleware), `backend/tests/` (header assertions)

---

## Tier 1 — Get Found

*Discovery work. Unchanged in intent from the original Sprint 0, with one addition that everything else now depends on: the schedule is fetched client-side, so Google cannot read it.* — **that gap is closed; #46 has shipped.** The rest of the tier builds on top of it.

### 5. Add structured data (Schema.org LocalBusiness)
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** SEO

Add JSON-LD marking the site as a `BarOrPub` with name, address, phone, `geo` coordinates for Montañita, and — the part that used to be free — `openingHoursSpecification` built from the live weekly hours plus any upcoming closures. This is the highest-impact SEO change for a local business, because it is what produces the knowledge panel and the map pin. It depends on #46: the hours are now in the database and change without a deploy, so hardcoding them in `index.html` would be wrong within a week.

**Files:** `frontend/index.html` (JSON-LD block), depends on `46` and `6` (phone/address)

---

### 6. Display phone number and address prominently
**Impact:** 🔴 · **Effort:** 🟢 · **Category:** UX

The "Find us" section has a map link and a town name, but no phone number and no street address — `src/lib/data.js` holds only `name`, `full`, `town`, and `mapsUrl`. A tourist deciding whether to walk there needs to know the address, and anyone who wants to confirm they have the right place needs to call. Add `phone` and `address` to `BAR`, render a clickable `tel:` link and the full address, and add a "Call now" button that is prominent on mobile. This ticket also unblocks #2, #5, and #47, which all need the same two fields.

**Files:** `frontend/src/lib/data.js` (`BAR` object), `frontend/src/App.svelte` (Visit section), `frontend/src/content/en.js` + `es.js`

---

### 2. Add WhatsApp floating button
**Impact:** 🔴 · **Effort:** 🟢 · **Category:** Growth

WhatsApp is the primary communication channel in Ecuador and the bar has no WhatsApp link at all. Add a floating action button — bottom-right on mobile, bottom-left on desktop — opening `wa.me` with a pre-filled message. Blocked on the phone number from #6; implement them together. Keep it out of the way of the surf widget and make sure it respects `env(safe-area-inset-bottom)` so it does not sit under the iOS home indicator.

**Files:** `frontend/src/App.svelte`, `frontend/src/lib/data.js`, `frontend/src/app.css`

---

### 47. Set up a Google Business Profile
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** SEO

Not a code ticket, and arguably the single highest-return hour in this list. A Google Business Profile drives the map pack, which outranks the website for "bar near me" searches. Needs the same phone and address from #6, a category, opening hours, and photos. The hard part is not creating it — it is keeping it updated, and the hours are now editable in the admin panel rather than in a browser tab, so export them or link the profile from the site for visitors to check.

**Files:** no code — needs `phone`/`address` from `6`; document the checklist in `docs/`

---

### 3. Add Open Graph / social preview tags
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Growth

Shared links currently render as a bare URL. Add `og:title`, `og:description`, `og:image`, `og:type`, `og:locale`, and Twitter card tags, plus a 1200x630 brand card image. Note that `App.svelte` already rewrites `<title>` and the meta description from the i18n store on load, which does nothing for crawlers — OG tags need to live in the static `index.html`. With bilingual content, emit `og:locale:es_EC` and an `alternate` link alongside the English default.

**Files:** `frontend/index.html`, new `frontend/public/og-image.png`

---

### 4. Add analytics
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Analytics

Still flying blind on where visitors come from. Plausible (privacy-friendly, no cookie banner needed, and the right default for a site that must load on slow Ecuadorian mobile connections) or GA4. Track referral sources and especially outbound clicks — WhatsApp, Instagram, TikTok, the map link — because those are the conversions that matter. With the backend now able to serve from one origin, a server-side Plausible proxy is available if third-party script blocking is a concern.

**Files:** `frontend/index.html`, `frontend/src/lib/analytics.js` (new, event helpers)

---

### 48. robots.txt, sitemap.xml & canonical URLs
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** SEO

There is no `robots.txt` or sitemap, and the admin panel is only unlinked — it is not excluded from crawling. `/admin`, `/admin/login`, and `/admin/schedule` should be disallowed. The admin templates already carry `<meta name="robots" content="noindex, nofollow">`, which helps but is not a substitute. Serve a sitemap listing the site and, once #16 lands, the menu route. Canonical URLs become relevant at the same time — today there is one page and four anchor targets that all resolve to `/`.

**Files:** new `frontend/public/robots.txt`, new sitemap route or static file, `backend/app/main.py`

---

### 9. Add proper favicon and app icons
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Design

The favicon is an emoji wave inlined as an SVG data URI in `index.html`, and the admin panel repeats the same trick. Replace with a branded mark in 16x16, 32x32, 180x180, 192x192 and 512x512. The 192 and 512 sizes are also the icons #31's manifest needs, so do this first. `frontend/public/` exists and is currently empty, which is where they go.

**Files:** `frontend/index.html`, `frontend/public/icons/`, `backend/app/templates/admin/dashboard.html`, `backend/app/templates/login.html`

---

## Tier 2 — Sell the Drinks

*The revenue core. The menu is the flagship ticket: the biggest gap in the business, and the first real test of the admin-panel pattern now that it exists.*

### 1. Add a drinks menu page
**Impact:** 🔴 · **Effort:** 🟡 · **Category:** Functionality

The bar sells beer, wine, liquor and cocktails, and the site has zero drink information. Build it the same way `events` and `hours` were built, not as a hardcoded array: add `menu_categories` and `menu_items` tables, a `/admin/menu` page in the style of `admin/schedule.html`, write endpoints behind the existing `write_guard`, and `GET /api/menu` for the public read. Then render a menu section on the site. Every visitor-facing string follows the existing bilingual convention — `name_en`/`name_es`, `description_en`/`description_es` — so `pick()` from `api.js` works unchanged and a half-translated menu still renders.

`docs/bar_menu.md` already contains real prices and is the **starting** menu, not the finished one: seed it into `app/seed.py` alongside the existing schedule seed, then treat completing it as part of the ticket. That file lists beer, coffee, soft drinks and cigarettes, and has no cocktails, wine, spirits or food at all. Confirm the current list and prices with the bar before seeding, and remove the cigarette line from the public menu unless it is genuinely still sold.

**Files:** `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/seed.py`, new route in `backend/app/routers/api.py`, new `backend/app/templates/admin/menu.html`, `backend/app/admin_i18n.py`, `backend/app/migrate.py`, new `frontend/src/lib/Menu.svelte`, `frontend/src/App.svelte`, `frontend/src/content/en.js` + `es.js`, source data `docs/bar_menu.md`

---

### 17. Content tables for promos, packages & gallery
**Impact:** 🔴 · **Effort:** 🟡 · **Category:** Operations

Originally "add a headless CMS (Sanity, Contentful, Strapi)". That was the right instinct and the wrong instrument — the site already has a database, an admin panel, authentication, CSRF, and a bilingual field convention. Adding a third-party CMS would mean maintaining two sources of truth for content that the existing admin panel already handles well. Instead, extract the pattern from #1 into a small set of generic content tables that #7, #20, #22 and #8 all reuse: a `content_sections` / `content_items` pair with `slug`, bilingual `title`/`body`, an optional price, a sort order, an optional date window, and an `is_active` flag. One admin page that lists sections and edits items in place. This ticket is what makes the rest of Tiers 2 and 3 editable without a developer.

**Files:** `backend/app/models.py`, `backend/app/migrate.py`, `backend/app/schemas.py`, new `backend/app/templates/admin/content.html`, `backend/app/admin_i18n.py`, `backend/app/static/admin_i18n.js`

---

### 16. Create separate menu page (multi-page structure)
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Architecture

The site is a single page with four anchor targets. That was right when it was a static brochure; it stops being right when there is a menu, a gallery and a contact form. The menu needs its own URL so it can be shared on Instagram and WhatsApp, so Google can index it separately, and so it can carry its own meta tags and JSON-LD (see #49). Two viable routes: a lightweight hash or history router in the SPA, or real server-side routes served by FastAPI alongside the existing static mount. The second is better for SEO and costs little now that the backend is already serving the site — but it means the menu must render without a client-side fetch, so it overlaps deliberately with #46.

**Files:** `frontend/src/App.svelte`, new `frontend/src/lib/router.js` or server routes in `backend/app/main.py`

---

### 49. Menu SEO (Menu schema & indexable menu route)
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** SEO

Once #16 and #1 land, the menu is a page Google can read — and a bar menu is exactly the content people search for. Emit `Menu` and `FoodEstablishment`-adjacent JSON-LD for the menu route, including each item's name, description and `offers.price` in USD. Requires the menu HTML to be server-rendered (from #46/#16), not client-fetched. Verify with Google's Rich Results Test before calling it done. Low effort relative to how often "drinks menu Montañita" gets typed into a phone at 9pm.

**Files:** menu route from `16`, JSON-LD block, `frontend/src/content/en.js` + `es.js`

---

### 7. Add happy hour / daily promos section
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Functionality

The bar runs promos on different days and the site does not mention them. Now that content is editable (#17), promos become rows rather than a code change — the owner updates "Tuesday: 2x1 cocktails 5–7pm" from the admin panel instead of asking a developer. Model recurring promos by weekday, reusing the `events.day` convention, plus a one-off override table for dates. If a promo has a date window, show it only inside that window so stale promos never linger.

**Files:** `backend/app/models.py`, `backend/app/routers/api.py`, `frontend/src/App.svelte`, `frontend/src/content/en.js` + `es.js`

---

### 18. Add drink pricing and descriptions
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Content

Deliberately kept as a separate ticket from menu because it is content work, not engineering, and can be done by anyone with access to the admin panel. Add price and a description to every menu item, with proper detail for signature cocktails — ingredients, flavour profile, the story behind it. Positioning Marea Alta as a cocktail destination rather than a beach bar is the entire point, and a menu of bare names and numbers does not do it. `docs/bar_menu.md` has prices but no descriptions, so both are still outstanding.

**Files:** `backend/app/templates/admin/menu.html` (fields from #1), data in the `menu_items` table

---

### 11. Add food menu section
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Functionality

If the bar serves food — snacks, ceviche, burgers — add it as a second set of `menu_categories` rows rather than a separate table. The schema built in #1 is category-driven, so this is mostly a data-entry task plus a filter toggle on the menu section. Even a short snack menu raises average spend and time on site. If food is genuinely minimal, list what exists and move on.

**Files:** `backend/app/seed.py`, `frontend/src/lib/Menu.svelte`, `frontend/src/App.svelte`

---

### 30. Add "Drinks We're Known For" signature section
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Content

Highlight 3–5 drinks that cannot be got anywhere else, with photos and the story behind each. Given a reason to try something specific, and gives the social media team a standing content slot. Set `is_active` on the rows so the selection rotates seasonally without a deploy. Distinct from #18: that ticket fills in descriptions for everything, this one curates a handful into a homepage slot.

**Files:** `frontend/src/lib/Signature.svelte`, `frontend/src/App.svelte`, `menu_items` rows with `is_featured`

---

### 10. Add a "Drink of the Day" hero banner
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Engagement

Rotate a featured drink in the hero, with name, one line and price. Give people a reason to come *today* rather than "sometime". Because it is a row in the database, the owner can change it in ten seconds — and the daily rotation can be done from the admin panel rather than by editing `data.js`. Also the obvious source of the daily Instagram post, so it serves the social channel as well as the site.

**Files:** `backend/app/models.py` (or reuse #17 content tables), `frontend/src/App.svelte`, `frontend/src/content/en.js` + `es.js`

---

### 22. Add birthday / package deals
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Revenue

Birthdays are a large share of Montañita's party scene. Publish 2–3 package tiers — bottle, mixers, a cocktail for the birthday person, a song — with prices, using the content tables from #17. Each gets a "Book your birthday" CTA opening WhatsApp with the package name pre-filled, which ties back to #2. High impact, almost no engineering, and it captures bookings that currently go to the bar next door.

**Files:** `backend/app/seed.py`, `frontend/src/lib/Packages.svelte`, `frontend/src/App.svelte`

---

### 19. Add "About Us" section
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Content

Tell the story: when it opened, why "Marea Alta", how it connects to Montañita's surf culture. Keep it authentic — this is a surf bar, not a corporate site. Once #17 lands this is admin-editable bilingual text rather than a deploy, which also means it can be updated when the story changes. Include the surf connection explicitly, since that is the differentiator and it is already the site's premise.

**Files:** `frontend/src/lib/About.svelte`, `frontend/src/App.svelte`, `frontend/src/content/en.js` + `es.js`

---

### 20. Add private events / group booking info
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Revenue

Surface private event offerings: capacity, packages, pricing, how to book, plus a photo of a past event. Substantially cheaper than the original estimate now that content is database-backed — most of this ticket is writing and one photo. Pair it with #14 so the booking path is the same one used for ordinary reservations rather than a second mechanism.

**Files:** `frontend/src/lib/Events.svelte`, `frontend/src/App.svelte`, `backend/app/templates/admin/content.html`

---

## Tier 3 — Convert & Retain

*Turn a visitor into a conversation. The backend makes these dramatically cheaper than the original estimates — most are now one table and one endpoint.*

### 15. Add contact form
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Functionality

Dropped from 🟡 to 🟢 because the backend exists. The original ticket weighed a `mailto:` hack against "a more advanced setup with a backend endpoint" — the second option is now just a table, one `POST` endpoint, and a form. Fields: name, contact, subject, message. Needs abuse protection before it goes live (see the rate-limit note in #12) and a way for the bar to actually see submissions, which is #51.

**Files:** new `submissions` table in `backend/app/models.py`, new route in `backend/app/routers/api.py`, new `frontend/src/lib/ContactForm.svelte`, `frontend/src/App.svelte`, `frontend/src/content/en.js` + `es.js`

---

### 12. Add email capture / newsletter signup
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Growth

Also dropped to 🟢 for the same reason: a `subscribers` table and one endpoint. The remaining question is delivery — Mailchimp/Buttondown for the list, or an occasional export from the admin panel if the volume stays small. Decide when building. **Abuse protection is required here, not optional:** the login rate limiter in `app/routers/auth.py` covers only `/admin/login`, is an in-process dict, and counts failed attempts — none of which helps against a script hitting a public signup form. Add IP rate limiting and a honeypot field, and consider a CAPTCHA if spam arrives anyway. Every public write endpoint added in this tier needs this treatment.

**Files:** new `subscribers` table, new route in `backend/app/routers/api.py`, `frontend/src/lib/Newsletter.svelte`, `backend/app/templates/admin/subscribers.html`

---

### 51. Notify the bar when a submission arrives
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Operations

Added because #12, #14 and #15 are all incomplete without it. A reservation request that lands in a database nobody checks is worse than no form at all — it creates false confidence that bookings are being taken. Send an email and/or WhatsApp notification to the owner the moment a submission arrives, and surface an unread count on the admin dashboard, which is currently just a link card. Include a one-click reply-to so responding takes seconds. If no notification path can be made reliable, at minimum show submissions on the dashboard with a loud count.

**Files:** `backend/app/routers/api.py`, `backend/app/templates/admin/dashboard.html`, new notification module in `backend/app/`, `backend/app/config.py`

---

### 14. Add reservation / table booking system
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Functionality

For weekends and events when the bar fills. Start with the WhatsApp deep link from #2, pre-filled with date, time and party size — that is genuinely most of the value for none of the work. If the bar wants to track bookings rather than just take messages, add a `reservations` table with date, time, party size, name and status, an admin view to confirm or decline, and #51's notification. Note that this will collide with #25 (RSVP) unless one booking model is chosen — settle that in #53.

**Files:** new `reservations` table, new routes in `backend/app/routers/api.py`, new `backend/app/templates/admin/reservations.html`, `frontend/src/lib/Reservation.svelte`, `frontend/src/lib/data.js`

---

### 52. Emergency notice banner
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Functionality

New capability the backend makes possible and worth its effort. Power cut, storm closure, sold-out event, a guest who needs to know the kitchen is closed: today the only way to tell anyone is a social post that most visitors never see. Add a `notices` table with bilingual text, an active window and a severity, an admin control to set and clear it, and a banner on the site that appears above everything when active. This is the highest-value use of the admin panel per line of code, because it is the one thing that matters when it is wrong — and it is exactly the scenario `closed_days` only partly covers (#42).

**Files:** new `notices` table, new routes in `backend/app/routers/api.py`, `backend/app/templates/admin/dashboard.html`, `frontend/src/App.svelte`, `frontend/src/content/en.js` + `es.js`

---

### 50. Image upload pipeline
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Infrastructure

A blocker for #8, #30 and #22, none of which can be delivered without a way to get an image into the system. There is currently no file handling anywhere in the codebase and `frontend/public/` is empty, so this is greenfield. Add an admin-only upload endpoint storing files outside the repo, validate type and size server-side, resize and re-encode to WebP with a thumbnail, and serve them through a route that sets caching headers. Store paths in the database, not blobs — the SQLite file should stay small enough to back up with the cron from #38. Reuse the same bilingual caption fields as everything else.

**Files:** new upload module in `backend/app/`, new routes in `backend/app/routers/api.py`, new `backend/app/templates/admin/uploads.html`, `backend/app/config.py`, `frontend/src/lib/`

---

### 8. Add photo gallery
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Functionality

Now depends on #50 rather than being pure frontend work, so the effort rose from 🟢 to 🟡. Bars sell on atmosphere, and the site has no photographs. A grid or simple carousel of signature cocktails, the interior, the crowd at night, the beach view and the surf — managed through the admin panel so new photos can be added without a deploy. Lazy-load and serve WebP via #50. Keep it to roughly 12–20 images; a gallery of forty identical beach shots reads as filler.

**Files:** `frontend/src/lib/Gallery.svelte`, `frontend/src/App.svelte`, `backend/app/models.py`, images under the path from `50`

---

### 13. Embed Instagram feed
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Social Media

The site links to Instagram but shows none of its content. Embed a live feed via Elfsight or SnapWidget (both have free tiers and handle the token refresh that breaks hand-rolled embeds). Shows the bar is active without anyone maintaining anything. Weigh against #50: if the gallery from #8 is admin-managed and good, it may already answer "is this place active" without a third-party widget and its cookie banner. Decide before building.

**Files:** new `frontend/src/lib/InstagramFeed.svelte`, `frontend/src/App.svelte`, `frontend/index.html`

---

### 53. Dated / special events
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Functionality

A genuine gap in the data model. `events` is one row per weekday — a permanently repeating weekly pattern. There is no way to express "Friday the 26th — DJ Sol", a one-off themed party, or a party that moves to a different night for a month. Add a `special_events` table with a date, bilingual title and description, optional time override and an image, and render them in the schedule alongside the weekly entries. This unblocks #26 and gives #25 something to attach RSVP and ticket links to. Decide here whether one-off events also own the `reservations` model from #14, or stay separate.

**Files:** `backend/app/models.py`, `backend/app/migrate.py`, `backend/app/schemas.py`, new routes in `backend/app/routers/api.py`, `backend/app/seed.py`, `frontend/src/App.svelte`

---

### 25. Add event ticketing / RSVP
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Functionality

For bigger events, let people RSVP so the bar can gauge attendance and reduce no-shows. Requires #53's dated events first — there is nothing dated to attach a ticket to today. For paid tickets, Eventbrite or Ticket Tailor is cheaper than building payments; for free RSVP, a `rsvps` table plus an admin guest count is enough. Keep the RSVP and reservation models distinct unless #53 says otherwise.

**Files:** new `rsvps` table, `backend/app/routers/api.py`, `backend/app/templates/admin/`, `frontend/src/App.svelte`

---

### 26. Add live music calendar
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Functionality

Depends on #53. The weekly schedule shows recurring parties but live music nights deserve artist names, genres and set times. With a dated-events table this is mostly a calendar view over real rows, optionally synced from Bandsintown so artist data updates itself. Include artist photos and social links, using #50's upload path.

**Files:** new `frontend/src/lib/Calendar.svelte`, `frontend/src/App.svelte`, `special_events` from `53`

---

## Tier 4 — Grow the Business

*Community and retention features. Each needs staff discipline more than code — a loyalty card nobody stamps or a quiz nobody links to is inert. Kept in the backlog deliberately, sequenced after the tickets above.*

### 21. Add loyalty program
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Retention

Reward repeat visitors. A digital punch card — buy nine, get the tenth — is the simple version: a `loyalty` table keyed by phone number or email, a QR code the customer scans, and a counter the staff increments. The backend makes the storage trivial and the admin panel makes redeeming a drink a two-click job. The hard part is operational: somebody has to run it every shift. Promote it on the site and on a small card at the bar.

**Files:** new `loyalty` table, `backend/app/templates/admin/loyalty.html`, `frontend/src/lib/Loyalty.svelte`, `frontend/src/App.svelte`

---

### 24. Add blog / news section
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** SEO

Organic traffic from search: upcoming events, new drink recipes, surf conditions, Montañita travel tips. The infrastructure is nearly free now — posts are content rows in #17's tables, with a date and a slug. The cost is writing one post a month, indefinitely, and a blog with three posts from 2023 is worse than none. Only start this once there is a committed writer. Each post is then a shareable link for the Instagram account from #13.

**Files:** new `posts` table in `backend/app/models.py`, new `frontend/src/lib/Blog.svelte`, `frontend/src/lib/BlogPost.svelte`, post routes from `16`

---

### 28. Add user-generated content (photo contest)
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Social Media

A monthly contest — visitors post their best photo with a hashtag, the winner gets a bottle or a bar tab — displayed on the site with permission. Generates free content and gives people a reason to visit and post. Needs consent handling, which is the real work here: an explicit opt-in on submission, not an assumption. Manual selection and manual publishing via the admin panel is fine at this scale; do not build a moderation queue.

**Files:** new `frontend/src/lib/Contest.svelte`, `frontend/src/App.svelte`, `backend/app/templates/admin/content.html`, rules text in `frontend/src/content/en.js` + `es.js`

---

### 29. Add referral program
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Growth

"Bring a friend, both get a drink." Word-of-mouth is the strongest marketing in a town this size. Give each regular a unique code, store the referral in `loyalty` (#21) rather than a parallel system, and reward on redemption. Promote on the site and on a card at the bar. Sequence after #21 — the same table serves both, and building them separately means two implementations of the same idea.

**Files:** extends `21` — `backend/app/models.py`, `backend/app/templates/admin/loyalty.html`, `frontend/src/lib/Referral.svelte`

---

### 27. Add "Perfect Drink" quiz / recommendation
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Engagement

Three or four questions — mood, sweet versus strong, beer versus cocktail — ending in a signature recommendation. Highly shareable, and it walks new visitors past the generic options. Rules live as a JSON column or a small config table; results resolve against the `menu_items` rows from #1, so a drink being sold out disappears from the quiz automatically. Keep it light and fun.

**Files:** new `frontend/src/lib/Quiz.svelte`, `frontend/src/App.svelte`, quiz rules as data, resolves against `GET /api/menu`

---

### 23. Add merch / store section
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Revenue

T-shirts, hats, stickers, koozies — an extra revenue stream that turns visitors into walking advertisements. List items with photos from #50 and an "Order via WhatsApp" button (#2) rather than building checkout; Printful or Printify handle fulfilment if there is volume. Needs #50 and a size/colour variant decision for anything wearable.

**Files:** new `frontend/src/lib/Merch.svelte`, `frontend/src/App.svelte`, `backend/app/templates/admin/content.html`, images from `50`

---

## Tier 5 — Operate & Polish

*Keeping the thing running once it carries real traffic and real money.*

### 35. Expand automated testing
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Quality

Partially delivered already — there are roughly 920 lines of tests: `backend/tests/` covers auth and sessions, CSRF, the schedule and closed-days CRUD, migrations and end-to-end admin-edit propagation; `frontend/src/` has Vitest coverage of the language fallback, time formatting and a regression guard proving the schedule re-renders on language switch without a remount. What is missing is everything above unit level. Add Playwright for the paths that would actually cost money if broken: the menu renders and prices are right, the language toggle works, an admin edit reaches the public page, a reservation submits. Add coverage reporting and let #36 gate on it. Note the SQLite concurrency test from #43 belongs here too.

**Files:** new `frontend/e2e/`, `frontend/playwright.config.js`, new `backend/tests/test_concurrency.py`, `frontend/package.json`, `.github/workflows/ci.yml`

---

### 37. Add error tracking (Sentry)
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** DevOps

When something breaks you need to know immediately. Sentry's free tier covers both tiers here, which matters because the failure modes are now split: a frontend exception leaves the visitor with a half-rendered page, and a backend exception leaves them with a cached schedule and a "showing cached data" notice that looks like a minor annoyance until nobody can see the bar is open. Capture both. Tag backend errors with the route and the admin action, and alert only on the endpoints that make the site work. Worth doing before #16 multiplies the surface area.

**Files:** `frontend/src/main.js`, new `backend/app/` Sentry init, `frontend/package.json`, `backend/requirements.txt`, `backend/app/config.py`

---

### 54. Admin password change & second admin
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Security

Right now the only way to change a password or add a user is the `manage_admin.py` CLI, which means SSH access to the box. If the bar owner loses that access they are locked out of their own site entirely, and if they want a second person managing the schedule they cannot grant it. Add a change-password page and a create-admin page behind the existing session guard, with password strength rules and invalidating the user's other sessions on change. Session revocation is worth including — `sessions` rows are already keyed by `admin_id`, so it is a delete.

**Files:** new routes in `backend/app/routers/admin.py` or `auth.py`, new `backend/app/templates/admin/account.html`, `backend/app/auth.py`, `backend/app/admin_i18n.py`, `backend/tests/test_auth.py`

---

### 55. Audit log of admin edits
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Operations

With more than one admin (#54) and more content types in the database (#17, #53), there is no way to answer "who changed Friday's hours to 4pm and when". Add an `audit_log` table capturing admin id, action, target, before/after JSON and timestamp, written in the same transaction as the change. Display recent entries on the dashboard. Cheap insurance against accidental edits and the only defence when two people are editing the same schedule.

**Files:** new `audit_log` table in `backend/app/models.py`, `backend/app/routers/api.py`, `backend/app/routers/admin.py`, `backend/app/templates/admin/dashboard.html`

---

### 33. Accessibility pass
**Impact:** ⚪ · **Effort:** 🟡 · **Category:** Design

An audit across both tiers, which is why the scope grew: images need alt text, contrast must meet WCAG AA, interactive elements must be keyboard-navigable, ARIA labels must be correct. The public site already has some good habits — focus-visible rings, `aria-label`s, semantic sections. The admin panel is un-audited and is where a keyboard-only user would struggle most, particularly the save-on-blur fields in `admin/schedule.html`. The right thing to do, and broader in reach than the original single-tier estimate.

**Files:** `frontend/src/App.svelte`, `frontend/src/lib/*.svelte`, `frontend/src/app.css`, `backend/app/templates/admin/*.html`, `backend/app/templates/login.html`

---

### 34. Performance optimizations
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Efficiency

Optimise for slow mobile connections on the Ecuadorian coast: lazy-load gallery images from #50, cache hashed build assets hard at the nginx layer (#41), gzip or brotli text responses, and preload the fonts. Target Lighthouse 90+ on mobile. Two specifics: `Surf.svelte` calls the Open-Meteo APIs from the visitor's browser on every page load, so proxying and caching that server-side removes a third-party round trip from the critical path; and the schedule is re-fetched hourly, so confirm the response is small enough that the periodic refresh is invisible.

**Files:** `frontend/src/lib/Surf.svelte`, `frontend/vite.config.js`, `deploy/nginx.conf`, `backend/app/routers/api.py`

---

### 31. Add PWA support
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** UX

Make the site installable. Add a web app manifest and a service worker with an offline strategy, plus an install prompt. The schedule's `localStorage` cache in `api.js` already degrades gracefully, so the service worker can cache the shell and the last-known schedule and the site still shows something on a bad connection. Update the old note that this requires HTTPS from GitHub Pages — TLS now comes from #41's Let's Encrypt step. Reuse the icons from #9.

**Files:** new `frontend/public/manifest.json`, new `frontend/public/sw.js`, `frontend/index.html`, `frontend/src/App.svelte`

---

### 56. Data export / import (CSV)
**Impact:** ⚪ · **Effort:** 🟡 · **Category:** Operations

Once the menu, promos, packages, events and reservations all live in the database, the bar's real content is only inside the app. Export the content tables to CSV from the admin panel for offline editing and bulk correction, and support import with per-row validation so a bad file cannot corrupt live content. Pairs with #38: a readable export is also the fallback if the database is ever lost and the scheduled restore has not been run.

**Files:** new export/import routes in `backend/app/routers/admin.py`, `backend/app/templates/admin/`, `backend/app/schemas.py`

---

### 40. Add CDN in front of the server
**Impact:** ⚪ · **Effort:** 🟡 · **Category:** Efficiency

Rewritten for the new architecture. The original rationale was "GitHub Pages already uses a CDN" — that is no longer true, because the site is served from a VPS. Cloudflare's free tier in front of the origin now adds DDoS protection, TLS termination, asset caching and image optimisation, and it hides the origin IP. Only worth it once traffic is real enough to matter; nginx alone from #41 handles caching in the meantime.

**Files:** DNS configuration, Cloudflare dashboard, `deploy/nginx.conf`

---

### 32. Add dark mode toggle
**Impact:** ⚪ · **Effort:** 🟢 · **Category:** Design

The surf section already uses a dark palette. Add a toggle between light and dark, persisted in `localStorage` alongside the existing `lang` preference, defaulting to `prefers-color-scheme`. Most relevant for night-time browsing, which is exactly when someone decides where to go out. Keep it low priority — it is the least costly ticket here and the least likely to change behaviour.

**Files:** `frontend/src/app.css` (CSS variables), `frontend/src/App.svelte` (toggle), `frontend/src/lib/i18n.js` (preference persistence)

---

## Summary Table

(✅ completed, ⏳ in progress, 🚫 blocked, 🧪 waiting testing, ❌ wontfix, blank for not started)

Ordered by tier. Ticket numbers are not sequential — the original 40 kept their numbers and moved.

| Status | # | Ticket | Impact | Effort | Category |
|:------:|---|--------|:------:|:------:|----------|
| | 41 | Deploy the backend to production | 🔴 | 🟡 | DevOps |
| | 42 | Fix closed-day handling on the public site | 🔴 | 🟢 | Functionality |
| | 43 | Harden SQLite for concurrent production writes | 🔴 | 🟢 | DevOps |
| | 44 | Production environment & secrets runbook | 🟠 | 🟢 | Operations |
| | 36 | CI/CD rebuild | 🔴 | 🟡 | DevOps |
| | 38 | Automated database backups & restore drill | 🔴 | 🟢 | DevOps |
| | 39 | Uptime monitoring & health endpoint | 🟠 | 🟢 | DevOps |
| | 45 | Security headers: HSTS & CSP | 🟠 | 🟢 | Security |
| ✅ | 46 | Server-render schedule & hours for crawlers | 🔴 | 🟡 | SEO |
| | 5 | Add structured data (Schema.org) | 🟠 | 🟢 | SEO |
| | 6 | Display phone number and address | 🔴 | 🟢 | UX |
| | 2 | Add WhatsApp floating button | 🔴 | 🟢 | Growth |
| | 47 | Set up a Google Business Profile | 🟠 | 🟢 | SEO |
| | 3 | Add Open Graph / social preview tags | 🟠 | 🟢 | Growth |
| | 4 | Add analytics | 🟠 | 🟢 | Analytics |
| | 48 | robots.txt, sitemap.xml & canonical URLs | 🟡 | 🟢 | SEO |
| | 9 | Add proper favicon and app icons | 🟡 | 🟢 | Design |
| | 1 | Add a drinks menu page | 🔴 | 🟡 | Functionality |
| | 17 | Content tables for promos, packages & gallery | 🔴 | 🟡 | Operations |
| | 16 | Create separate menu page (multi-page) | 🟠 | 🟡 | Architecture |
| | 49 | Menu SEO (Menu schema & indexable route) | 🟠 | 🟡 | SEO |
| | 7 | Add happy hour / daily promos | 🟠 | 🟢 | Functionality |
| | 18 | Add drink pricing and descriptions | 🟠 | 🟢 | Content |
| | 11 | Add food menu section | 🟡 | 🟡 | Functionality |
| | 30 | Add signature drinks section | 🟡 | 🟢 | Content |
| | 10 | Add "Drink of the Day" banner | 🟡 | 🟢 | Engagement |
| | 22 | Add birthday / package deals | 🟠 | 🟢 | Revenue |
| | 19 | Add "About Us" section | 🟡 | 🟢 | Content |
| | 20 | Add private events / group booking | 🟡 | 🟡 | Revenue |
| | 15 | Add contact form | 🟠 | 🟢 | Functionality |
| | 12 | Add email capture / newsletter | 🟠 | 🟢 | Growth |
| | 51 | Notify the bar on new submissions | 🟠 | 🟡 | Operations |
| | 14 | Add reservation / booking system | 🟠 | 🟡 | Functionality |
| | 52 | Emergency notice banner | 🟠 | 🟡 | Functionality |
| | 50 | Image upload pipeline | 🟠 | 🟡 | Infrastructure |
| | 8 | Add photo gallery | 🟠 | 🟡 | Functionality |
| | 13 | Embed Instagram feed | 🟠 | 🟡 | Social Media |
| | 53 | Dated / special events | 🟠 | 🟡 | Functionality |
| | 25 | Add event ticketing / RSVP | 🟡 | 🟡 | Functionality |
| | 26 | Add live music calendar | 🟡 | 🟡 | Functionality |
| | 21 | Add loyalty program | 🟠 | 🟡 | Retention |
| | 24 | Add blog / news section | 🟡 | 🟡 | SEO |
| | 28 | Add photo contest / UGC | 🟡 | 🟡 | Social Media |
| | 29 | Add referral program | 🟡 | 🟡 | Growth |
| | 27 | Add "Perfect Drink" quiz | 🟡 | 🟡 | Engagement |
| | 23 | Add merch / store section | 🟡 | 🟡 | Revenue |
| | 35 | Expand automated testing | 🟠 | 🟡 | Quality |
| | 37 | Add error tracking (Sentry) | 🟠 | 🟡 | DevOps |
| | 54 | Admin password change & second admin | 🟠 | 🟢 | Security |
| | 55 | Audit log of admin edits | 🟡 | 🟡 | Operations |
| | 33 | Accessibility pass | ⚪ | 🟡 | Design |
| | 34 | Performance optimizations | 🟠 | 🟡 | Efficiency |
| | 31 | Add PWA support | 🟠 | 🟡 | UX |
| | 56 | Data export / import (CSV) | ⚪ | 🟡 | Operations |
| | 40 | Add CDN in front of the server | ⚪ | 🟡 | Efficiency |
| | 32 | Add dark mode toggle | ⚪ | 🟢 | Design |

---

## Suggested Sprint Order

**The order has changed at the front.** The original Sprint 0 was "Get found" — menu, OG tags, analytics. That was correct when the site was static and the only thing between it and revenue was marketing. It is no longer correct: the backend has never been deployed, the deploy workflow fails on every push, and the SQLite configuration will throw under concurrent writes. Shipping SEO work onto a site that is not reliably serving it wastes the effort.

**Sprint 0 — "Get it running" (1 week)**
Tickets 41, 42, 43, 44, 38, 45.
*Goal: The site is deployed, reachable over HTTPS, safe from data loss, and the two closed-day bugs are fixed. Six tickets — four of them under a day — because none of the rest matters until this is true.*

**Sprint 1 — "Survive deploys" (1 week)**
Tickets 36, 39, 35.
*Goal: Every change is tested and deployed automatically, and a failure pages someone. Fixes the broken CI in #36 and closes the gap #35 leaves.*

**Sprint 2 — "Get found" (1–2 weeks)**
Tickets ~~46~~, 5, 6, 2, 47, 3, 4, 48, 9.
*Goal: Make the bar discoverable. #46 is done — the schedule and hours are in the HTML. #5 and #6 build on it.*

**Sprint 3 — "Sell the drinks" (2 weeks)**
Tickets 1, 17, 16, 49, 7, 18, 11, 30, 10.
*Goal: The menu exists, the owner can edit it, and it is shareable and indexable. #1 and #17 are the load-bearing pair; #16 and #49 follow once there is a page worth indexing.*

**Sprint 4 — "Convert" (2 weeks)**
Tickets 15, 12, 51, 14, 52, 50, 8, 13, 22, 19, 20.
*Goal: Turn visitors into conversations. #51 is not optional — forms without a notification channel are worse than no form. #50 unlocks #8.*

**Sprint 5 — "Events & community" (2–3 weeks)**
Tickets 53, 25, 26, 21, 24, 28, 29, 27, 23.
*Goal: One-off events, then community and retention. #53 must precede #25 and #26 — there is nothing dated to attach them to until it lands.*

**Sprint 6 — "Operate & polish" (2 weeks)**
Tickets 37, 54, 55, 33, 34, 31, 56, 40, 32.
*Goal: Reliable, accessible, fast. Do this before high season, not during.*

---

# Completed Tickets

*Move finished tickets here and mark them ✅ in the Summary Table. Items below predate this backlog and were shipped before it was rebuilt.*

## Server-rendered schedule (#46)
**Shipped** — The homepage is rendered by FastAPI rather than served off disk. `app/ssr.py` reads `frontend/dist/index.html` and injects the current week — tonight's party, every day's title, description and opening hours, and any closure notices — as plain HTML inside `#app`, so a crawler receives it without executing anything. The same payload is handed to the SPA as `window.__MAREA_ALTA_DATA__`, so the first paint needs no request and the visitor never sees a loading state; the app replaces the block on mount. Rendering happens at request time rather than at build time, because the hours are editable from the admin panel and a build-time render would publish stale ones. `?lang=es` renders the Spanish block, `Cache-Control: no-cache` keeps it current, and the JSON API and the HTML are served from one set of loaders so they cannot disagree.

## The bilingual schedule system
**Shipped** — Weekly party schedule, opening hours and one-off closed days are managed in the SQLite database and edited from a bilingual admin panel at `/admin`. Public read endpoints (`GET /api/schedule`, `GET /api/closed-days`) return every string in both languages, so the frontend switches language without a second request. `pick()` falls back to English when a translation is blank. Non-destructive migrations in `app/migrate.py` upgrade legacy single-language content and normalise legacy `4:00 PM` times to `HH:MM`.

## Admin authentication & security
**Shipped** — bcrypt password hashing, server-side sessions in SQLite with random 64-char tokens and 8-hour expiry, HttpOnly + SameSite=Lax cookies (Secure in production), double-submit CSRF protection on all writes, login rate limiting, and a bilingual admin panel that is not linked from the public site.

## Automated testing foundations
**Shipped** — ~1,100 lines. `backend/tests/` covers auth and sessions, CSRF enforcement, the schedule and closed-days CRUD, migrations, the server-rendered homepage (including HTML escaping and admin-edit propagation), and end-to-end propagation of admin edits to the public read endpoints, running against an in-memory database so the real one is never touched. `frontend/src/` has Vitest coverage of the language fallback, time formatting, the server-rendered payload handover, a regression guard proving the app replaces the server-rendered block rather than stacking on it, and a guard keeping the server-rendered labels identical to the site's own wording. Expanded further by ticket #35.

## Production build pipeline
**Shipped** — Vite builds the frontend to `frontend/dist`, and the FastAPI app serves that directory from the same origin so the site and the API share a domain with no CORS and working cookies. `/` is rendered rather than served (see #46 above); the static mount is registered last so it only handles requests the API, admin and index routes did not claim. Deployment itself is ticket #41.