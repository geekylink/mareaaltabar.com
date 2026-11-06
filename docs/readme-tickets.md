# README-tickets.md

> **Companion to the Marea Alta Surf Bar website.** This document is the improvement backlog for the site. It was first written when Marea Alta was a static Svelte app with everything hardcoded in `src/lib/data.js`. The site now has a **FastAPI + SQLite backend**, a bilingual admin panel, and a public read API — so this list has been rebuilt around that reality.
>
> **What changed.** The original list assumed no backend. That made "add a CMS" and "add backups *if* you have a database" into large speculative projects. Both are now smaller and more concrete: the CMS is *this* database, and backups are a cron line. Meanwhile the backend introduced a class of work the original list never considered — deployment, database concurrency, secrets, and abuse of public write endpoints — which is why **Tier 0 now exists at all**.
>
> The business is still drinks. The original argument for putting the menu first held, and ticket **#1** — the flagship — has shipped: the menu is a database, an admin page and a `/menu` route.

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
  - [36. CI/CD rebuild](#36-cicd-rebuild)
- [Tier 1 — Get Found](#tier-1--get-found)
  - [5. Add structured data (Schema.org LocalBusiness)](#5-add-structured-data-schemaorg-localbusiness)
  - [6. Display phone number and address prominently](#6-display-phone-number-and-address-prominently)
  - [2. Add WhatsApp floating button](#2-add-whatsapp-floating-button)
  - [47. Set up a Google Business Profile](#47-set-up-a-google-business-profile)
  - [3. Add Open Graph / social preview tags](#3-add-open-graph--social-preview-tags)
  - [4. Add analytics](#4-add-analytics)
  - [9. Add proper favicon and app icons](#9-add-proper-favicon-and-app-icons)
- [Tier 2 — Sell the Drinks](#tier-2--sell-the-drinks)
  - [17. Content tables for promos, packages & gallery](#17-content-tables-for-promos-packages--gallery)
  - [16. Create separate menu page (multi-page structure)](#16-create-separate-menu-page-multi-page-structure)
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

**Since #46:** nginx must proxy `/` to uvicorn rather than serving `dist/index.html` itself — serving the file directly bypasses the server-rendered schedule and puts the hours back out of reach of crawlers. **Since #1 the same applies to `/menu`**, or the drinks disappear from the crawler's view too. `/assets/` can still be served from disk with a long cache lifetime.

**Files:** new `deploy/marea-alta.service`, new `deploy/nginx.conf`, `backend/README.md` (deploy section), `backend/.env`

---

### 36. CI/CD rebuild
**Impact:** 🔴 · **Effort:** 🟡 · **Category:** DevOps

The current workflow is broken rather than merely basic. It runs `npm ci` and `npm run build` at the repository root, where there is no `package.json`, then uploads `./dist` — a path that stopped existing when the project moved into `frontend/`. It also targets GitHub Pages, which can never host the API. Replace it with a pipeline that matches the architecture chosen in #41: build the frontend in `frontend/`, run both test suites (see #35), then deploy to the VPS over SSH. Add lint and type-check gates — `svelte-check` on the frontend, `ruff` on the backend — so a broken build cannot reach the server. Add `.github/workflows/ci.yml` for pull requests that runs checks without deploying.

**Files:** `.github/workflows/deploy.yml` (rewrite), new `.github/workflows/ci.yml`, `frontend/package.json` (add `lint`, `check` scripts), `backend/requirements.txt` (add `ruff`)

---

## Tier 1 — Get Found

*Discovery work. Unchanged in intent from the original Sprint 0, with one addition that everything else now depends on: the schedule is fetched client-side, so Google cannot read it.* — **that gap is closed; #46 has shipped.** The rest of the tier builds on top of it.

### 5. Add structured data (Schema.org LocalBusiness)
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** SEO

Add JSON-LD marking the site as a `BarOrPub` with name, address, phone, `geo` coordinates for Montañita, and — the part that used to be free — `openingHoursSpecification` built from the live weekly hours plus any upcoming closures. This is the highest-impact SEO change for a local business, because it is what produces the knowledge panel and the map pin. It depends on #46: the hours are now in the database and change without a deploy, so hardcoding them in `index.html` would be wrong within a week.

**Since #42:** `GET /api/closed-days` hands over today-and-later only, so this ticket no longer needs a date filter of its own — and a closure dated today can be expressed as today's hours rather than quietly dropped.

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

### 9. Add proper favicon and app icons
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Design

The favicon is an emoji wave inlined as an SVG data URI in `index.html`, and the admin panel repeats the same trick. Replace with a branded mark in 16x16, 32x32, 180x180, 192x192 and 512x512. The 192 and 512 sizes are also the icons #31's manifest needs, so do this first. `frontend/public/` exists and is currently empty, which is where they go.

**Files:** `frontend/index.html`, `frontend/public/icons/`, `backend/app/templates/admin/dashboard.html`, `backend/app/templates/login.html`

---

## Tier 2 — Sell the Drinks

*The revenue core. The menu has shipped (#1) — what is left is filling it out, and making it indexable.*

### 17. Content tables for promos, packages & gallery
**Impact:** 🔴 · **Effort:** 🟡 · **Category:** Operations

Originally "add a headless CMS (Sanity, Contentful, Strapi)". That was the right instinct and the wrong instrument — the site already has a database, an admin panel, authentication, CSRF, and a bilingual field convention. Adding a third-party CMS would mean maintaining two sources of truth for content that the existing admin panel already handles well. Instead, extract the pattern from #1 into a small set of generic content tables that #7, #20, #22 and #8 all reuse: a `content_sections` / `content_items` pair with `slug`, bilingual `title`/`body`, an optional price, a sort order, an optional date window, and an `is_active` flag. One admin page that lists sections and edits items in place. This ticket is what makes the rest of Tiers 2 and 3 editable without a developer.

Note that #1 has already established the half of this that matters most — the bilingual `_en`/`_es` convention, the availability flag, the sort order and the admin page pattern are all in `menu_categories` / `menu_items`. The remaining question is whether promos and packages get their own tables or become more `menu_categories`.

**Files:** `backend/app/models.py`, `backend/app/migrate.py`, `backend/app/schemas.py`, new `backend/app/templates/admin/content.html`, `backend/app/admin_i18n.py`, `backend/app/static/admin_i18n.js`

---

### 16. Create separate menu page (multi-page structure)
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Architecture

**Mostly landed with #1.** The menu now has its own URL at `/menu`, served as a second Vite entry point (`frontend/menu.html` → `MenuPage.svelte`) and rendered server-side by FastAPI, so it is a real document a crawler can read rather than a client-side view — which is the option this ticket called the better one. `vite.config.js` declares both entry points, so adding a third is a line of configuration.

What is left: the site is still a single page with anchor targets everywhere else (surf, party, visit), and nothing routes between documents yet. There is no client-side navigation, so moving to a gallery or a contact form still means either a hard link or a router.

**Files:** `frontend/vite.config.js` (entry points), `frontend/menu.html` + `frontend/src/menu-main.js` (landed), `frontend/src/App.svelte`

---

### 7. Add happy hour / daily promos section
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Functionality

The bar runs promos on different days and the site does not mention them. `menu_item_promos` from #1 already holds an offer label under a price, but it has no *when*: a happy-hour promo is "Tuesday 17:00–19:00", and a promo that is only valid in a window has to stop rendering when the window closes. Add a recurring window by weekday, reusing the `events.day` convention, plus a one-off override table for dates. Decide whether a timed promo is a new table or columns on `menu_item_promos` — the existing rows already hold the label, so extending them is probably the smaller change.

**Files:** `backend/app/models.py`, `backend/app/routers/api.py`, `frontend/src/lib/Menu.svelte`, `backend/app/templates/admin/menu.html`

---

### 18. Add drink pricing and descriptions
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Content

Deliberately kept as a separate ticket from menu because it is content work, not engineering, and can be done by anyone with access to the admin panel. **Prices are done** — `docs/bar_menu.md` was seeded in #1. What is outstanding is the description on every drink, and real detail for the signature cocktails: ingredients, flavour profile, the story behind it. Positioning Marea Alta as a cocktail destination rather than a beach bar is the entire point, and a menu of bare names and numbers does not do it. `ingredients_en` / `ingredients_es` exist and are live for the cocktails section; the cocktail list currently holds only the Cuba Libre.

**Files:** data in the `menu_items` table, via `backend/app/templates/admin/menu.html`

---

### 11. Add food menu section
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Functionality

If the bar serves food — snacks, ceviche, burgers — add it as another `menu_categories` row. The schema built in #1 is category-driven, so this is now **pure data entry**: create the category at `/admin/menu`, type the items in, done. The panel creates and renames categories itself, and an empty category is hidden from the site until it has something in it — which is how "Wine" and "Liquor" are already seeded and empty, waiting. Even a short snack menu raises average spend and time on site. If food is genuinely minimal, list what exists and move on.

**Files:** none — admin panel only

---

### 30. Add "Drinks We're Known For" signature section
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Content

Highlight 3–5 drinks that cannot be got anywhere else, with photos and the story behind each. Given a reason to try something specific, and gives the social media team a standing content slot. #1 built the tables this needs but not the selection flag — `menu_items` has `is_available`, which is about whether a drink is being sold, not whether it is the one being pushed. Add an `is_featured` column (and a migration for it), so the selection rotates seasonally without a deploy. Distinct from #18: that ticket fills in descriptions for everything, this one curates a handful into a homepage slot. Blocked on #50 for the photos.

**Files:** `backend/app/models.py` + `backend/app/migrate.py` (add `is_featured`), `frontend/src/lib/Signature.svelte`, `frontend/src/App.svelte`

---

### 10. Add a "Drink of the Day" hero banner
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Engagement

Rotate a featured drink in the hero, with name, one line and price. Give people a reason to come *today* rather than "sometime". Because it is a row in the database, the owner can change it in ten seconds — and the daily rotation can be done from the admin panel rather than by editing `data.js`. The ingredient and description fields from #1 give the banner something to say; #30's `is_featured` flag, or a separate column, is what picks the drink.

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

Three or four questions — mood, sweet versus strong, beer versus cocktail — ending in a signature recommendation. Highly shareable, and it walks new visitors past the generic options. Rules live as a JSON column or a small config table; results resolve against the `menu_items` rows from #1, so a drink being sold out disappears from the quiz automatically — `GET /api/menu` already withholds anything with `is_available` cleared. Keep it light and fun.

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

Partially delivered already — there are roughly 1,400 lines of tests: `backend/tests/` covers auth and sessions, CSRF, the schedule, closed-days and drinks-menu CRUD, the bilingual admin strings, migrations and end-to-end admin-edit propagation into both the JSON API and the rendered HTML; `frontend/src/` has Vitest coverage of the language fallback, time and price formatting, the menu component, and a regression guard proving the schedule and the menu re-render on language switch without a remount. What is missing is everything above unit level. Add Playwright for the paths that would actually cost money if broken: the menu renders and prices are right, the language toggle works, an admin edit reaches the public page, a reservation submits. Add coverage reporting and let #36 gate on it. Note the SQLite concurrency test from #43 belongs here too.

**Files:** new `frontend/e2e/`, `frontend/playwright.config.js`, new `backend/tests/test_concurrency.py`, `frontend/package.json`, `.github/workflows/ci.yml`

---

### 37. Add error tracking (Sentry)
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** DevOps

When something breaks you need to know immediately. Sentry's free tier covers both tiers here, which matters because the failure modes are now split: a frontend exception leaves the visitor with a half-rendered page, and a backend exception leaves them with a cached schedule and a "showing cached data" notice that looks like a minor annoyance until nobody can see the bar is open. Capture both. Tag backend errors with the route and the admin action, and alert only on the endpoints that make the site work. Worth doing before #16 multiplies the surface area.

**Files:** `frontend/src/main.js`, new `backend/app/` Sentry init, `frontend/package.json`, `backend/requirements.txt`, `backend/app/config.py`

---

### 55. Audit log of admin edits
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Operations · **Status:** ✅ Shipped

With more than one admin (#54) and more content types in the database (#17, #53), there is no way to answer "who changed Friday's hours to 4pm and when". Add an `audit_log` table capturing admin id, action, target, before/after JSON and timestamp, written in the same transaction as the change. Display recent entries on the dashboard. Cheap insurance against accidental edits and the only defence when two people are editing the same schedule.

**Files:** new `audit_log` table in `backend/app/models.py`, `backend/app/routers/api.py`, `backend/app/routers/admin.py`, `backend/app/templates/admin/dashboard.html`

**Shipped** — `login_attempts` and `audit_log` tables, written by `app/audit.py` and added to every write handler in the same transaction as the change; a read-only `/admin/logs` page with three logs (login attempts, menu changes, schedule changes) behind a menu bar, fed by GET-only endpoints in `backend/app/routers/logs.py`; username, IP and user agent on every row; a diff of only the fields that actually changed; and a 90-day retention purge, run daily at 07:00 at the bar or manually with `manage_admin.py purge-logs`.

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
| ✅ | 42 | Fix closed-day handling on the public site | 🔴 | 🟢 | Functionality |
| ✅ | 43 | Harden SQLite for concurrent production writes | 🔴 | 🟢 | DevOps |
| ✅ | 44 | Production environment & secrets runbook | 🟠 | 🟢 | Operations |
| | 36 | CI/CD rebuild | 🔴 | 🟡 | DevOps |
| ✅ | 38 | Automated database backups & restore drill | 🔴 | 🟢 | DevOps |
| ✅ | 39 | Uptime monitoring & health endpoint | 🟠 | 🟢 | DevOps |
| ✅ | 45 | Security headers: HSTS & CSP | 🟠 | 🟢 | Security |
| ✅ | 46 | Server-render schedule & hours for crawlers | 🔴 | 🟡 | SEO |
| | 5 | Add structured data (Schema.org) | 🟠 | 🟢 | SEO |
| | 6 | Display phone number and address | 🔴 | 🟢 | UX |
| | 2 | Add WhatsApp floating button | 🔴 | 🟢 | Growth |
| | 47 | Set up a Google Business Profile | 🟠 | 🟢 | SEO |
| ✅ | 3 | Add Open Graph / social preview tags | 🟠 | 🟢 | Growth |
| | 4 | Add analytics | 🟠 | 🟢 | Analytics |
| ✅ | 48 | robots.txt, sitemap.xml & canonical URLs | 🟡 | 🟢 | SEO |
| ✅ | 9 | Add proper favicon and app icons | 🟡 | 🟢 | Design |
| ✅ | 1 | Add a drinks menu page | 🔴 | 🟡 | Functionality |
| ✅ | 17 | Content tables for promos, packages & gallery | 🔴 | 🟡 | Operations |
| ✅ | 16 | Create separate menu page (multi-page) | 🟠 | 🟢 | Architecture |
| ✅ | 49 | Menu SEO (Menu schema & indexable route) | 🟠 | 🟢 | SEO |
| ✅ | 7 | Add happy hour / daily promos | 🟠 | 🟢 | Functionality |
| | 18 | Add drink pricing and descriptions | 🟠 | 🟢 | Content |
| | 11 | Add food menu section | 🟡 | 🟢 | Functionality |
| | 30 | Add signature drinks section | 🟡 | 🟢 | Content |
| ✅ | 10 | Add "Drink of the Day" banner | 🟡 | 🟢 | Engagement |
| | 22 | Add birthday / package deals | 🟠 | 🟢 | Revenue |
| | 19 | Add "About Us" section | 🟡 | 🟢 | Content |
| | 20 | Add private events / group booking | 🟡 | 🟡 | Revenue |
| ✅ | 15 | Add contact form | 🟠 | 🟢 | Functionality |
| ✅ | 12 | Add email capture / newsletter | 🟠 | 🟢 | Growth |
| | 51 | Notify the bar on new submissions | 🟠 | 🟡 | Operations |
| ✅ | 14 | Add reservation / booking system | 🟠 | 🟡 | Functionality |
| ✅ | 52 | Emergency notice banner | 🟠 | 🟡 | Functionality |
| ✅ | 50 | Image upload pipeline | 🟠 | 🟡 | Infrastructure |
| | 8 | Add photo gallery | 🟠 | 🟡 | Functionality |
| | 13 | Embed Instagram feed | 🟠 | 🟡 | Social Media |
| ✅ | 53 | Dated / special events | 🟠 | 🟡 | Functionality |
| ✅ | 25 | Add event ticketing / RSVP | 🟡 | 🟡 | Functionality |
| ✅ | 26 | Add live music calendar | 🟡 | 🟡 | Functionality |
| | 21 | Add loyalty program | 🟠 | 🟡 | Retention |
| | 24 | Add blog / news section | 🟡 | 🟡 | SEO |
| | 28 | Add photo contest / UGC | 🟡 | 🟡 | Social Media |
| | 29 | Add referral program | 🟡 | 🟡 | Growth |
| ✅ | 27 | Add "Perfect Drink" quiz | 🟡 | 🟡 | Engagement |
| | 23 | Add merch / store section | 🟡 | 🟡 | Revenue |
| | 35 | Expand automated testing | 🟠 | 🟡 | Quality |
| | 37 | Add error tracking (Sentry) | 🟠 | 🟡 | DevOps |
| ✅ | 54 | Admin password change & second admin | 🟠 | 🟢 | Security |
| ✅ | 55 | Audit log of admin edits | 🟡 | 🟡 | Operations |
| | 33 | Accessibility pass | ⚪ | 🟡 | Design |
| | 34 | Performance optimizations | 🟠 | 🟡 | Efficiency |
| ✅ | 31 | Add PWA support | 🟠 | 🟡 | UX |
| ✅ | 56 | Data export / import (CSV) | ⚪ | 🟡 | Operations |
| | 40 | Add CDN in front of the server | ⚪ | 🟡 | Efficiency |
| | 32 | Add dark mode toggle | ⚪ | 🟢 | Design |

---

## Suggested Sprint Order

**The order has changed at the front.** The original Sprint 0 was "Get found" — menu, OG tags, analytics. That was correct when the site was static and the only thing between it and revenue was marketing. It is no longer correct: the backend has never been deployed, the deploy workflow fails on every push, and the SQLite configuration will throw under concurrent writes. Shipping SEO work onto a site that is not reliably serving it wastes the effort.

**Sprint 0 — "Get it running" (1 week)**
Tickets 41, ~~42~~, ~~43~~, ~~44~~, ~~38~~, ~~45~~.
*Goal: The site is deployed, reachable over HTTPS and safe from data loss. #42–#45 are done — the closed-day bugs are fixed, SQLite is hardened, the production environment is documented and the security headers ship. Only #41 remains, and none of the rest matters until the site is actually serving.*

**Sprint 1 — "Survive deploys" (1 week)**
Tickets 36, ~~39~~, 35.
*Goal: Every change is tested and deployed automatically, and a failure pages someone. Fixes the broken CI in #36 and closes the gap #35 leaves.*

**Sprint 2 — "Get found" (1–2 weeks)**
Tickets ~~46~~, 5, 6, 2, 47, ~~3~~, 4, ~~48~~, ~~9~~.
*Goal: Make the bar discoverable. #46 is done — the schedule and hours are in the HTML. #3 and #9 are also done. #5 and #6 build on it.*

**Sprint 3 — "Sell the drinks" (1 week)**
Tickets ~~1~~, 18, 11, ~~49~~, ~~7~~, ~~17~~, ~~16~~, ~~10~~.
*Goal: The menu exists, the owner can edit it, and it is indexable. ~~#1~~ is done — the menu is a database, an admin page and a `/menu` route — and ~~#49~~ added the `Menu` JSON-LD. ~~#7~~, ~~#17~~, ~~#16~~ and ~~#10~~ are also done. What is left is content (#18, #11).*

**Sprint 4 — "Convert" (2 weeks)**
Tickets ~~15~~, ~~12~~, 51, ~~14~~, ~~52~~, ~~50~~, 8, 13, 22, 19, 20.
*Goal: Turn visitors into conversations. ~~#15~~, ~~#12~~, ~~#14~~ and ~~#50~~ are done. #51 is now the missing half — forms without a notification channel are worse than no form. #8 still needs real photographs.*

**Sprint 5 — "Events & community" (2–3 weeks)**
Tickets 53, 25, 26, 21, 24, 28, 29, ~~27~~, 23.
*Goal: One-off events, then community and retention. #53 must precede #25 and #26 — there is nothing dated to attach them to until it lands. ~~#27~~ is done — the quiz scores the live menu, so a removed drink drops out of the recommendations.*

**Sprint 6 — "Operate & polish" (2 weeks)**
Tickets 37, ~~54~~, 55, 33, 34, 31, ~~56~~, 40, 32.
*Goal: Reliable, accessible, fast. #54 is done — the owner can manage passwords and a second admin without SSH. ~~#56~~ is done — every content table can be exported and re-imported safely. Do the rest before high season, not during.*

---

# Completed Tickets

*Move finished tickets here and mark them ✅ in the Summary Table. Items below predate this backlog and were shipped before it was rebuilt.*

## Shared navigation (#16)
**Shipped** — `frontend/src/lib/Nav.svelte` is now the one header for `/` and `/menu`, including the logo link and the language selector. On the homepage it emits in-page anchors; on the menu document it emits `/#surf`, `/#party`, `/#contact` and `/#visit` and deliberately drops the menu item the visitor is already on. The old duplicated markup and styles were removed from `App.svelte` and `MenuPage.svelte`. `frontend/src/lib/nav.test.js` covers both link bases, a reduced link list and the Spanish labels.

## Drink of the Day (#10)
**Shipped** — `menu_items.is_drink_of_day` is a boolean with a migration, editable from `/admin/menu`. The item write handlers clear the flag on every other row when a save sets it, so the hero can only have one answer even if two saves race in sequence. The public API and `load_menu()` carry the flag, and `DrinkOfDay.svelte` reads it from the menu `App.svelte` has already loaded rather than making a second request; a switched-off or unmarked drink renders nothing. There is no date scheduling: “of the day” lasts until the owner changes it. `backend/tests/test_api_menu.py` and `frontend/src/lib/drinkOfDay.test.js` cover the one-at-a-time rule and the hero copy.

## Generic content tables (#17)
**Shipped** — `content_sections` and `content_items` hold generic bilingual content: a slug, title and body per language, an optional price, image URL, inclusive date window, sort order and active flag. `GET /api/content` and `GET /api/content/{slug}` publish only live sections with live rows and drop a heading with nothing under it; `GET /api/content/all` is session-guarded and keeps switched-off and expired rows editable. `/admin/content` edits sections and rows in place, including reorder, and every write lands in the new content log (`/api/logs/content`, fourth tab on `/admin/logs`). Images are URLs because the upload pipeline (#50) is not built, and there is no public layout for these rows yet. `backend/tests/test_content.py` covers the public/admin split, date windows, URL validation, slug conflicts, cascade delete and audit rows.

## Newsletter signup (#12)
**Shipped** — A `subscribers` table stores a lower-cased unique address, optional name, consent timestamp, IP and user agent. `POST /api/newsletter` requires the consent checkbox, uses the contact form's honeypot and a separate per-IP rate limiter, and returns the same success shape for a duplicate address without creating a second row. `/admin/subscribers` lists subscribers with active/total counts, unsubscribes or re-subscribes without deleting, deletes, and exports only the active list as CSV. There is no delivery provider, double opt-in or emailed unsubscribe link yet — the CSV export is the handoff. `backend/tests/test_newsletter.py` and `frontend/src/lib/newsletter.test.js` cover the guards and the form payload.

## Reservation requests (#14)
**Shipped** — A `reservations` table stores a bar-local date, time, party size, name, contact and notes. `POST /api/reservations` accepts today through 90 days ahead and 1–20 guests, uses a honeypot and a per-IP limiter, and always creates a `pending` row — this is a request, not a booking. `/admin/reservations` filters by status, confirms, declines, returns to pending and deletes; the dashboard shows a pending badge. No guest notification is sent because #51 is still blocked on provider credentials. `backend/tests/test_reservations.py` and `frontend/src/lib/reservation.test.js` cover validation, the queue and the request-not-booking copy.

## Event RSVPs (#25)
**Shipped (free RSVP only)** — A separate `rsvps` table attaches a name, contact, party of 1–20 and notes to one `special_events` row; deleting the event cascades to its guest list. `POST /api/special-events/{id}/rsvp` is public, honeypot-protected and rate-limited per IP, and returns 404 for hidden, past or unknown events so a stranger cannot discover an unannounced party. Each event on the homepage gets an expandable RSVP form, and `/admin/rsvps` filters by event and shows both the number of RSVPs and the total number of people coming. Paid tickets are deliberately delegated to Eventbrite or Ticket Tailor; there is no payment, ticket code or guest notification (#51). `backend/tests/test_rsvp.py` and `frontend/src/lib/rsvp.test.js` cover validation, the event-state rules, the honeypot, rate limiting, the admin counts and cascade deletion.

## PWA support (#31)
**Shipped** — `frontend/public/manifest.json` makes the site installable with the existing 192 and 512 icons, standalone display and the brand colours. `frontend/public/sw.js` precaches the shell and an `offline.html` fallback, then uses network-first for navigations and the five public API reads (`/api/schedule`, `/api/closed-days`, `/api/menu`, `/api/notices`, `/api/special-events`), cache-first for hashed assets and `/uploads/`, and leaves `/admin` and every admin API read alone. Both entry points register the worker in production only. `InstallPrompt.svelte` shows a strip only when Chromium fires `beforeinstallprompt` and then uses the browser's own prompt. Installation requires HTTPS (or localhost); TLS comes from the deploy step. Bump `VERSION` in `sw.js` when the shell changes so the old cache is dropped. `frontend/src/pwa.test.js` and `frontend/src/lib/installPrompt.test.js` cover the manifest, the cache rules and the prompt.

## Live music calendar (#26)
**Shipped** — The homepage's flat special-events list is now a month calendar over the dated events from #53. It opens on the soonest event's month (not necessarily today), marks event days, pages forwards and backwards, and shows the selected day's bilingual title, time, description, optional image and RSVP form. The week starts on Sunday to match the schedule. Artist names and genres live in the event title and description; there is no separate artist table, social-link field or Bandsintown sync. `frontend/src/lib/calendar.test.js` covers the initial month, day selection, month paging, the empty month and Spanish.

## “Perfect Drink” quiz (#27)
**Shipped** — A three-question quiz on the homepage asks mood (cold and easy, cocktail, wine, surprise), taste (sweet, strong, fresh, no preference) and how the night is going. `frontend/src/lib/quizRules.js` scores the menu the visitor already loaded: a matching category is a strong signal, bilingual name/description/ingredient keywords break ties, and the cigarette category is excluded. Because it resolves against `GET /api/menu` data, a drink the owner hides or removes stops being recommended without a second list to maintain. The result shows the drink's name, category, price, description and ingredients, can be restarted, and shares through the Web Share API with a clipboard fallback. Answers and results are not stored. Rules are a plain module rather than a table so the copy can change without a migration. `frontend/src/lib/quizRules.test.js` and `frontend/src/lib/quiz.test.js` cover the scoring, the cigarette exclusion, the empty menu, the full flow, sharing and Spanish.

## CSV export and import (#56)
**Shipped** — `/admin/data` downloads seven CSV tables: menu categories, menu items, menu promos, content sections, content items, special events and reservations. The export carries a UTF-8 BOM so Excel reads Spanish accents correctly. Import is all-or-nothing: every row is validated with the same Pydantic models as the admin forms, and a file with one bad row changes nothing. Rows update by id (or by slug for categories and sections), a blank id creates a new row, and a row missing from the file is never deleted. Menu items resolve their category by slug, content items their section by slug, and promos their item by id. Setting `is_drink_of_day` on one row clears every other row, matching the menu editor. Every created or changed row is written to the same audit log as a panel edit. Reservations are export-only because they are public requests, not editable content. `backend/tests/test_csv_data.py` covers the page and access guards, every export shape, round-trips, creation, invalid-row rollback, missing columns, unknown ids and slugs, the drink-of-day rule, past-event correction and audit rows.

## Image upload pipeline (#50)
**Shipped** — `POST /api/uploads` is admin + CSRF only, accepts JPEG/PNG/WebP/GIF up to 10 MB, reads the format from the bytes rather than the request header, refuses decompression bombs by pixel count, applies EXIF orientation and re-encodes to WebP at 1600 px plus a 480 px thumbnail. Files are written under `UPLOAD_DIR` (default `backend/data/uploads`, an absolute path outside the repo in production) with random names; the `uploads` table stores only metadata and the two filenames. `GET /uploads/<name>.webp` serves the image with a one-year immutable cache header, and `/admin/uploads` uploads, edits bilingual captions and deletes. Uploads are logged in the content area. `backend/tests/test_uploads.py` covers the happy path, access control, format/size/pixel rejection, traversal, caption sanitisation and file cleanup.

## Open Graph and social preview tags (#3)
**Shipped** — Static `og:*` and Twitter card tags on `index.html` and `menu.html`, plus generated 1200×630 preview images. `frontend/src/seo.test.js` guards the tags and assets.

## Favicon and app icons (#9)
**Shipped** — A branded SVG, 16/32/180/192/512 PNGs and a multi-size `.ico`. The old emoji data-URI favicon is gone from the public pages and every admin template, and `backend/tests/test_assets.py` keeps the icon set and templates in step.

## Happy hour and daily promos (#7)
**Shipped** — `menu_item_promos` gained weekday, time (including overnight), date and active windows. Public API/SSR and the SPA publish only live offers; the admin read keeps every offer with `is_live`, and `/admin/menu` edits each window. Tests: `test_api_menu.py`, `test_migrations.py`, `test_ssr.py`, `menu.test.js`.

## Contact form and shared admin inbox (#15)
**Shipped** — Public `POST /api/contact` with sanitisation, a 1,000-character cap, honeypot and per-IP rate limiting; messages land in the shared `/admin/inbox` with read/unread, delete and a dashboard unread badge. Tests: `test_contact.py`, `contact.test.js`.

## Dated and special events (#53)
**Shipped** — `special_events` stores one-off dated events with bilingual title/description, optional time window, image URL and active switch. Upcoming live events render alongside the weekly schedule in the API and SSR; `/admin/events` edits everything, and writes are audited in the schedule area. Tests: `test_special_events.py`, `App.test.js`, `api.test.js`.

## Security headers: HSTS and CSP (#45)
**Shipped** — `app/main.py` generates a fresh `secrets.token_urlsafe(16)` nonce for every response, stores it on `request.state.csp_nonce`, and sends a CSP with `default-src 'self'`, no `'unsafe-inline'` or `'unsafe-eval'` in `script-src`, and explicit allowlists for Google Fonts (`style-src`, `font-src`) and both Open-Meteo hosts (`connect-src`). Every inline `<script>` in the login and admin templates, plus the server-rendered data seed and menu JSON-LD, carries that nonce; `ssr.render_index` and `ssr.render_menu` take it as an argument. `Permissions-Policy` turns off camera, microphone, geolocation, payment, USB and the other device APIs the site does not use. HSTS (`max-age=31536000; includeSubDomains`) is sent only when `ENVIRONMENT=production`, so a plain-HTTP development server cannot poison localhost. Swagger UI is exempt from the CSP in development because it loads from a CDN, and is disabled in production anyway. `backend/tests/test_security_headers.py` asserts the header set, the script policy, the external allowlists, a fresh nonce per response, matching nonces on the homepage, menu JSON-LD and every admin page, the production-only HSTS, and the docs exemption.

## Automated database backups and restore drill (#38)
**Shipped** — `scripts/backup.py` copies the SQLite database through `sqlite3.Connection.backup()`, the same consistent-snapshot mechanism as `sqlite3 .backup`, so a write in progress cannot tear the copy. `scripts/backup.sh` is the cron-friendly wrapper. Each run writes `marea_alta-YYYY-MM-DD.db` and a monthly `marea_alta-YYYY-MM.db`, verifies every file with `PRAGMA integrity_check` before atomically replacing the destination, and prunes only files matching those patterns — a stray file in the backup directory is left alone. Retention defaults to 14 daily and 12 monthly copies, adjustable with `--retain-days` and `--retain-months`; `--verify` re-checks one file or every backup in the directory. `docs/deployment.md` replaces the manual `sqlite3` recipe with the script, a nightly cron line, the off-box copy step and a restore drill that restores into a scratch database and confirms the schedule before touching the live file. `backend/tests/test_backup.py` covers the copy, a full restore, same-day replacement, retention bounds, unrelated files and corrupt-backup rejection.

## Emergency notice banner (#52)
**Shipped** — The owner can now put a message at the top of the site without a deploy. A `notices` table holds bilingual text, a severity (`info`, `warning`, `critical`), an optional bar-local start and end, and an `is_active` switch. `load_notices()` is the one place that decides whether a notice is live — switched on **and** inside its window — and both the public `GET /api/notices` and the server-rendered pages use it, so the banner a crawler reads and the banner the SPA renders cannot disagree. `GET /api/notices/all`, `POST`, `PUT` and `DELETE` are session- and CSRF-guarded; every write is logged in the schedule log as `notice:<id>`, so a fourth log tab was not needed. `/admin/notices` adds, pauses, resumes and deletes notices, and links from the dashboard. The banner renders above the hero on `/` and above the menu on `/menu`, on the first paint and after the SPA mounts; the payload is in `window.__MAREA_ALTA_DATA__` and the localStorage cache, with older cached payloads treated as "no notices" rather than crashing. `backend/tests/test_notices.py` covers the window, the public/admin split, validation, audit rows, server-rendered HTML in both languages and escaping; `frontend/src/lib/notice.test.js` covers language fallback, severity and the empty state.

## SQLite concurrency hardening (#43)
**Shipped** — `app/database.py` now builds the engine through `create_db_engine()`, which applies `journal_mode=WAL`, a 30-second `busy_timeout` and `foreign_keys=ON` on every connection. A second writer waits for the lock instead of raising `database is locked`, and readers keep working while a writer commits. The app still runs **one worker**; WAL improves the failure mode, it does not make SQLite multi-writer. `backend/README.md` no longer advertises `--workers 4`, and `backend/tests/test_concurrency.py` asserts the pragmas and drives four separate sessions writing at once.

## Uptime health endpoint (#39)
**Shipped** — `GET /healthz` runs `SELECT 1` through the normal database session and returns `200 {"status":"ok"}` or `503 {"status":"unavailable"}`, always with `Cache-Control: no-store`. It is public, cheap and does not expose the database error. The Dockerfile, `docker-compose.yml` and the container smoke test now point at `/healthz` instead of `/api/schedule`, and `backend/README.md` documents it as the endpoint for an external monitor. Pointing a monitor at the homepage would miss the exact failure that matters: a static page rendering while the API is down and the schedule is blank.

## robots.txt, sitemap and canonical URLs (#48)
**Shipped** — `frontend/public/robots.txt` disallows the admin panel and advertises the sitemap; `frontend/public/sitemap.xml` lists `/` and `/menu`. Both are copied into `dist/` by Vite and served by the existing static mount, so no backend route was needed. `index.html` and `menu.html` each carry one canonical URL on `https://mareaaltabar.com`, and `frontend/src/seo.test.js` validates the robots directives, the sitemap XML and both canonical tags. The assets remain available under Vite dev as well.

## Production environment and secrets runbook (#44)
**Shipped** — Removed the dead `SECRET_KEY` from `app/config.py` and the local `.env`: sessions are random tokens in the `sessions` table, so there is nothing to sign and nothing to rotate. `backend/README.md` now documents only the variables that exist, including the absolute `DATABASE_PATH`, `COOKIE_SECURE`, session lifetime and rate limits, and points at the new `docs/deployment.md`. The runbook covers the production `.env` template, file and directory permissions, TLS and cookie flags, the one-worker rule, admin bootstrap, `/healthz` monitoring, a nightly `sqlite3 .backup` cron entry and a restore drill. It also records that `.env` and `backend/data/` are gitignored, so no deployment secret or durable data lives in version control.

## Menu structured data (#49)
**Shipped** — `/menu` now emits a schema.org `Menu` graph built from the same `load_menu()` rows the visible menu uses: one `MenuSection` per category, one `MenuItem` per drink, the page's language in `inLanguage`, the description when one exists, and an `Offer` in USD when the stored price parses. Prices stay text in the database; `json_ld_price()` parses a plain amount at render time and returns `None` for anything else, so an unpriced drink gets no `offers` instead of a false `$0.00`. The JSON-LD is escaped with the same `<` → `\u003c` rule as the data seed, so an admin-entered item name cannot close the script element. `backend/tests/test_ssr.py` checks the graph, both languages, the offer shape, the unpriced case and the escaping.

## Admin password change and second admin (#54)
**Shipped** — `/admin/account` gives a signed-in admin two forms: change their own password (current password required, at least 8 characters with a letter and a number, and different from the old one) and create a second admin. Both POSTs require the session and the form's CSRF token, compared to the token stored on the session row rather than only to the readable cookie. A successful password change updates the hash and deletes every other session for that admin in the same transaction, keeping the current one signed in; a failed change leaves the old password working. Usernames are restricted to a safe character set, duplicates are caught by a pre-check and by the unique constraint, and the page is reachable from a dashboard card and the header of every admin page. Bilingual strings live in `admin_i18n.py`, and `backend/tests/test_account.py` covers the guards, the rules and the session revocation.

## The drinks menu (#1)
**Shipped** — The menu is now database content, built on the same pattern as `events`/`hours` rather than a hardcoded array. Three tables: `menu_categories` (bilingual name, unique `slug` for the anchor, sort order, `is_available`), `menu_items` (bilingual name/description/**ingredients**, price, sort order, `is_available`) and `menu_item_promos` (several multi-buy offers per drink, each bilingual). `/admin/menu` manages all three — add, rename, reorder and remove categories; add, edit, reorder and remove drinks; add and remove promo rows — with the same "filled EN / filled ES" colour bar the schedule page uses, and the same save-then-refetch discipline so the page always shows what the database holds. Public read is `GET /api/menu`; writes sit behind the existing `write_guard`.

Two calls worth recording. **A price is the headline figure only**: `docs/bar_menu.md` writes `$1.50 (6x $7.00)` in one column, and that became a price of `1.50` plus a promo row, so a drink can carry several offers and each is edited on its own — the bar's real packet prices for cigarettes work the same way. And **`is_available` is the reversible move**: clearing it withdraws a sold-out drink from the site without deleting it, which is why the panel reads from `/api/menu/all` (session required) rather than the public endpoint — a drink hidden from `/api/menu` would otherwise be invisible in the panel too, with no way to bring it back.

`docs/bar_menu.md` was seeded into `app/seed.py` alongside the schedule, so the site had real prices from the first deploy: seven beers, seven other drinks, two cigarettes, and a Cocktails section holding the Cuba Libre at $4.00 with its ingredients. **Wine and liquor are seeded empty** — the bar sells both, the document lists neither — and hidden from the site until something is added, which is also the proof that an empty category does not render as a bare heading.

The menu renders in both the places it should: as a section on the homepage, and at **`/menu`** as its own document. That is ticket #16's preferred option arriving early — a second Vite entry point, a FastAPI route, and server-rendered HTML, so the drinks are in the page a crawler reads and the URL is something you can post on WhatsApp. Both places render the same `Menu.svelte` from the same `load()`, so they cannot drift, and the crawler-visible block comes from the same `load_menu()` the API does.

**What is still open:** #18 (descriptions for every drink; the cocktail list beyond the Cuba Libre), #11 (food, which is now pure data entry), #30 and #10 (`is_featured`, which does not exist yet). **Since then:** #49 added the `Menu` JSON-LD, and the price stayed text — parsing at render time was enough.

## Closed-day handling on the public site (#42)
**Shipped** — `GET /api/closed-days` now returns today and later only, filtered in `load_closed_days()` — the loader the JSON API and the server-rendered homepage share — against the bar's own clock rather than the server's, so a closure stops being published the day after it happens and the two can never disagree about which days are shut. `ClosedDayCreate` refuses the same dates using that same clock, so the bar's own today is accepted even in the five-hour window where the server's date is already tomorrow. Past rows stay in the table but are never returned, which also means they no longer appear in the admin panel's closed-days list. On the site, a day can be shut three ways and all three now agree: the weekday's `is_closed` flag, a title of "Closed"/"Cerrado", and a closure dated today — merged into one `closedToday` flag that hides the Tonight card, replaces tonight's party in the week list with the closed label, and stops the Visit section claiming the bar is open until late. The crawler-visible HTML was fixed the same way, so the first paint and the live app agree instead of the page visibly changing on mount, and the client filters past dates too, because the `localStorage` cache and the embedded payload outlive the date they were fetched on.

## Server-rendered schedule (#46)
**Shipped** — The homepage is rendered by FastAPI rather than served off disk. `app/ssr.py` reads `frontend/dist/index.html` and injects the current week — tonight's party, every day's title, description and opening hours, and any closure notices — as plain HTML inside `#app`, so a crawler receives it without executing anything. Since #1 it also injects the drinks menu, and renders `frontend/dist/menu.html` the same way for the `/menu` route. The same payload is handed to the SPA as `window.__MAREA_ALTA_DATA__`, so the first paint needs no request and the visitor never sees a loading state; the app replaces the block on mount. Rendering happens at request time rather than at build time, because the hours and the menu are editable from the admin panel and a build-time render would publish stale ones. `?lang=es` renders the Spanish block, `Cache-Control: no-cache` keeps it current, and the JSON API and the HTML are served from one set of loaders so they cannot disagree.

## The bilingual schedule system
**Shipped** — Weekly party schedule, opening hours, one-off closed days and the drinks menu are managed in the SQLite database and edited from a bilingual admin panel at `/admin`. Public read endpoints (`GET /api/schedule`, `GET /api/closed-days`, `GET /api/menu`) return every string in both languages, so the frontend switches language without a second request. `pick()` falls back to English when a translation is blank. Non-destructive migrations in `app/migrate.py` upgrade legacy single-language content and normalise legacy `4:00 PM` times to `HH:MM`.

## Admin authentication & security
**Shipped** — bcrypt password hashing, server-side sessions in SQLite with random 64-char tokens and 8-hour expiry, HttpOnly + SameSite=Lax cookies (Secure in production), double-submit CSRF protection on all writes, login rate limiting, and a bilingual admin panel that is not linked from the public site. Since #54, password changes and second admins are managed at `/admin/account` rather than only through the CLI.

## Audit log of admin edits (#55)
**Shipped** — Two append-only tables, `login_attempts` and `audit_log`, written by `app/audit.py` and added to every write handler in `app/routers/api.py`. `/admin/logs` is a read-only page with three logs behind a menu bar: every login attempt (successes, wrong passwords, unknown usernames and rate-limited attempts alike, each with the username typed, the IP and the browser), every menu change, and every schedule change including closed days. A change and its log row are written in **one transaction**, so a change can never exist unrecorded, and the entry carries only the fields that actually moved — `price: 4.00 → 4.50` — so a week of "Save all days" presses on an untouched schedule cannot bury the one save that mattered. **The password is never passed to the logger**, and there is no column it could go in. Reads are GET-only and session-guarded: a `POST`, `PUT` or `DELETE` against `/api/logs/*` is a 405 rather than a rejected payload, which is what makes the page strictly read-only rather than read-only by convention.

Entries are kept for 90 days (`LOG_RETENTION_DAYS`), purged every day at 07:00 at the bar by a sleeping task in the app's `lifespan`, or by hand with `manage_admin.py purge-logs --days 90`. The purge is idempotent, so running it against a live multi-worker server — where every worker fires it at the same minute — costs a redundant `DELETE` that matches nothing and never an error.

**Since then:** #54 shipped the account page and a second-admin flow, so a row's username can now be one of several people — which is what makes attribution worth more than a single name on a row.

## Automated testing foundations
**Shipped** — ~1,400 lines. `backend/tests/` covers auth and sessions, CSRF enforcement, the schedule, closed-days and drinks-menu CRUD (including promo replacement, the availability split between the public and admin reads, and cascade deletes), the bilingual admin strings, migrations, the server-rendered homepage and `/menu` (including HTML escaping and admin-edit propagation), and end-to-end propagation of admin edits to the public read endpoints, running against an in-memory database so the real one is never touched. `frontend/src/` has Vitest coverage of the language fallback, time and price formatting, the menu component, the server-rendered payload handover, a regression guard proving the app replaces the server-rendered block rather than stacking on it, and a guard keeping the server-rendered labels identical to the site's own wording. Expanded further by ticket #35.

## Production build pipeline
**Shipped** — Vite builds the frontend to `frontend/dist`, and the FastAPI app serves that directory from the same origin so the site and the API share a domain with no CORS and working cookies. `/` and `/menu` are rendered rather than served (see #46 above); the static mount is registered last so it only handles requests the API, admin and page routes did not claim. Deployment itself is ticket #41.