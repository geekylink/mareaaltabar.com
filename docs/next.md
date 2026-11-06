# Next work — implementable in this environment

This file tracks the remaining backlog items that can be built and tested on the
current machine (no Docker, VPS, external accounts, or missing business data).
It is updated after every completed ticket.

Source of truth for the full backlog: [`readme-tickets.md`](readme-tickets.md).

## Completed in this batch

- **#3 Open Graph / social preview tags** — static `og:*` and Twitter card tags on
  `/` and `/menu`, plus generated 1200×630 preview images. Tests: `seo.test.js`.

## Remaining, ready to build here

| # | Ticket | Notes |
|---|--------|-------|
| 9 | Favicon and app icons | Generate SVG + 16/32/180/192/512 PNGs; replace emoji favicon in site and admin templates. |
| 7 | Happy hour / daily promos | Weekday/time/date windows on menu promos; live filtering; admin editing. |
| 15 | Contact form + shared admin inbox | `submissions` table, IP + user agent, 1,000-char message cap, sanitization, honeypot, rate limit, `/admin/inbox` for all admins. |
| 53 | Dated / special events | `special_events` table, public/admin API, SSR, frontend section, `/admin/events`. |
| 10 | Drink of the Day hero banner | Featured/daily menu item plus admin control. |
| 12 | Newsletter signup | `subscribers` table, public endpoint, admin list, abuse protection. |
| 14 | Reservation / booking system | `reservations` table, request endpoint, admin confirm/decline. |
| 16 | Multi-page navigation (remaining) | Shared cross-document navigation between `/` and `/menu`. |
| 17 | Generic content tables | Bilingual content sections/items plus one admin page. |
| 21 | Loyalty program | Punch-card table, admin counter/redeem, public signup/QR. |
| 25 | Event RSVP | After #53: RSVP table, endpoint, admin guest count. |
| 26 | Live music calendar | After #53: calendar over dated events. |
| 27 | “Perfect Drink” quiz | Frontend quiz resolving against `/api/menu`. |
| 29 | Referral program | After #21: codes and rewards on the loyalty table. |
| 31 | PWA support | Manifest + service worker + offline cache; after #9. |
| 32 | Dark mode toggle | CSS variables, toggle, persisted preference. |
| 33 | Accessibility pass | Public site and admin panel audit/fixes. |
| 34 | Performance optimizations | App-side: server-side surf proxy/cache, lazy loading, font preload. nginx caching is deploy-only. |
| 35 | Expanded automated testing | Playwright E2E + coverage; backend concurrency test already exists. |
| 36 | CI/CD rebuild (CI portion) | Rewrite workflow from `frontend/`, add PR CI and lint/check scripts. Deploy job needs VPS secrets. |
| 50 | Image upload pipeline | Admin upload, resize/WebP, storage outside repo, serving route. |
| 51 | Submission notification (fallback) | Shared inbox/unread count satisfies the useful half; email/WhatsApp needs a provider. |
| 56 | CSV export / import | Admin export/import with per-row validation. |

## Buildable, but needs owner content/assets/credentials

- **#8 Photo gallery** — engine can be built; needs photos and #50.
- **#30 Signature drinks** — `is_featured` + section; needs photos (#50).
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

1. **#9** Favicon and app icons
2. **#7** Happy hour / daily promos
3. **#15** Contact form + shared admin inbox
4. **#53** Dated / special events
