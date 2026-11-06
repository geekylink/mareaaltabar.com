# Still needed

Everything below is **not done**. It is either something only you can do (an
account, a credential, real business content, a decision) or something that
could not be verified on this machine. The code backlog that is still buildable
is listed separately at the end so it does not get mistaken for finished work.

Status at the time of writing: tickets **#3, #9, #7, #15, #53, #16, #10, #17,
#12, #14, #50, #25 and #31** are complete and committed. See [`docs/next.md`](docs/next.md)
for what was built and
[`docs/readme-tickets.md`](docs/readme-tickets.md) for the full backlog.

---

## 1. Deploy and operations (only you can do these)

The app is ready to deploy, but nothing has been deployed. No VPS, domain,
TLS certificate, DNS record or production database exists yet.

- [ ] **Get a VPS** and a Linux user for the service. Ticket **#41**.
- [ ] **Point the domain** `mareaaltabar.com` (and `www`) at the VPS. Ticket **#40**
      also covers any CDN/Cloudflare setup.
- [ ] **Create `backend/.env` on the server** from the template in
      [`docs/deployment.md`](docs/deployment.md). At minimum:
      `ENVIRONMENT=production`, an absolute `DATABASE_PATH` outside the repo,
      an absolute `UPLOAD_DIR` outside the repo, and `COOKIE_SECURE=true`
      **after** HTTPS works.
- [ ] **Install nginx and systemd**, proxy `/`, `/menu`, `/api` and `/admin` to
      uvicorn on `127.0.0.1:8000`, and serve `/assets/` from
      `frontend/dist/assets/`. Do **not** serve `index.html`/`menu.html`
      directly — that skips server-side rendering.
- [ ] **Issue a TLS certificate** (Let's Encrypt) and redirect HTTP to HTTPS.
      HSTS is production-only and should stay off until HTTPS is correct.
- [ ] **Set file permissions**: `chmod 600 backend/.env`, database directory
      owned by the service user with mode `750`.
- [ ] **Create the upload directory** (`UPLOAD_DIR`, e.g.
      `/var/lib/marea-alta/uploads`) owned by the service user. Uploaded images
      are **not** in the SQLite file, so the database backup does not include
      them: add the directory to the off-site copy as well.
- [ ] **Create the first admin** on the server:
      `python manage_admin.py create owner` (hidden password prompt).
- [ ] **Schedule backups** with `scripts/backup.sh` and copy them **off the box**
      (`rsync` to another host). A backup on the same disk is not a backup.
- [ ] **Run a restore drill** into a scratch directory before you need it.
- [ ] **Point an external uptime monitor** at `https://mareaaltabar.com/healthz`.
      Do not monitor `/`.
- [ ] **Set up log retention/cron** if you prefer `DAILY_LOG_PURGE=false` and
      `manage_admin.py purge-logs` from cron.
- [ ] **Verify the live headers** after deploy:
      `curl -sI https://mareaaltabar.com/ | grep -iE 'content-security-policy|strict-transport-security|permissions-policy'`.
- [ ] **Confirm `/`, `/menu` and `/admin/login`** on the real domain, including
      that the schedule/menu are in the page source before JavaScript runs.
- [ ] **Decide where the database lives** and who can read it. It contains admin
      password hashes, contact-form submissions (including IP and user agent)
      and audit logs.

## 2. Accounts, credentials and external services

These features are either stubbed, absent, or need a secret that does not exist
in this repo.

- [ ] **Sentry** — create a project and provide a DSN. Ticket **#37** is not
      built yet; no `SENTRY_DSN` is configured anywhere.
- [ ] **Analytics** — choose a provider (Plausible, Fathom, GA4, …) and provide
      the site ID/script. Ticket **#4** is not built.
- [ ] **Instagram feed** — the account/token or a third-party widget. Ticket
      **#13** is not built; only static profile links exist today.
- [ ] **Google Business Profile** — create/claim it and keep hours, photos and
      the website URL in sync. Ticket **#47** is external, non-code work.
- [ ] **Email delivery for contact and reservation notifications** — SMTP host,
      port, username, password and the destination address. Ticket **#51**
      currently stops at the shared `/admin/inbox` and the `/admin/reservations`
      queue; there is no email or WhatsApp notification.
- [ ] **Newsletter provider** — Mailchimp/Buttondown/other account and API key if
      you want signups to go anywhere automatically. For now the only path is
      the CSV export from `/admin/subscribers`. Ticket **#12**.
- [ ] **WhatsApp notifications/business number** — if you want submission or
      booking alerts by WhatsApp, provide the number and a provider/API token.
- [ ] **Domain/DNS access** — needed for the site, email (SPF/DKIM/DMARC) and any
      CDN in front of the server.
- [ ] **Backup destination** — SSH host/key or object-storage bucket for
      off-site copies.
- [ ] **Uptime-monitor account** — or confirm the VPS provider's monitor is
      enough.

## 3. Real business content and assets

The code can display these, but the real values are missing. Anything below
marked “placeholder” is a default in the seed or a label the site expects you to
fill in.

- [ ] **Phone number** — needed for the prominent contact block and
      `LocalBusiness` structured data. Tickets **#5** and **#6**.
- [ ] **Street address** — same tickets. The site currently links to Google Maps
      but does not print an address.
- [ ] **WhatsApp number** — for the floating button. Ticket **#2**.
- [ ] **Opening hours and weekly parties** — review the seeded defaults in
      `backend/app/seed.py` (`Latin Night`, `Singles Night`, closed Tue/Wed,
      etc.). They are a starting point, not confirmed facts.
- [ ] **Food menu** — the real dishes, descriptions and prices. Ticket **#11**;
      the code has no food section yet, and this is data entry once it exists.
- [ ] **Drink descriptions** — ticket **#18**. The admin panel already supports
      them; the text is missing.
- [ ] **Drink of the Day selection and copy** — pick the drink in
      `/admin/menu` and write its one-line description. The code supports one
      featured drink at a time; no drink is marked in the seed. Ticket **#10**.
- [ ] **Photos** — venue, drinks, events, gallery. The upload pipeline (#50) is
      ready, but there are still no real photographs. Tickets **#8**, **#30**,
      #53 and the generic content rows (#17) need images; a content row can use
      an uploaded URL or an external link.
- [ ] **“About Us” story** — the bar's history, founders, dates and tone.
      Ticket **#19**. The generic content tables are ready; only the copy is
      missing.
- [ ] **Package and gallery content** — real package tiers/prices and the first
      gallery rows for the #17 content tables. Tickets **#22**, **#8** and
      **#19**.
- [ ] **Signature drinks list** — which drinks go in “Drinks We're Known For”
      (and their photos). Ticket **#30**.
- [ ] **Birthday/package tiers** — real inclusions and prices. Ticket **#22**.
- [ ] **Private events/group bookings** — capacity, minimum spend, deposit and
      cancellation policy. Ticket **#20**.
- [ ] **Merch products** — items, sizes, colours, prices, stock and photos.
      Ticket **#23**.
- [ ] **Blog/news commitment** — who writes it, how often, and the first posts.
      Ticket **#24** needs an engine plus a committed writer.
- [ ] **Photo contest rules and consent wording** — eligibility, prizes, rights
      to republish, and how entrants consent. Ticket **#28**.
- [ ] **Loyalty programme rules** — punches per reward, expiry, whether rewards
      stack, and staff instructions. Ticket **#21**.
- [ ] **Reservation policy** — the code currently allows 1–20 guests, today to
      90 days ahead, always starts as `pending`, and has no deposit or no-show
      rule. Confirm or replace those defaults. Ticket **#14**.
- [ ] **Newsletter consent wording and unsubscribe route** — the form requires a
      ticked consent box and stores a consent timestamp, but there is no double
      opt-in, no unsubscribe link (the admin switch is the only one) and no
      privacy notice. Have the wording reviewed. Ticket **#12**.
- [ ] **Paid ticketing decision** — free RSVP is built (#25), but there is no
      paid ticket path, capacity limit, waitlist or guest notification. If a
      bigger event needs tickets, choose Eventbrite or Ticket Tailor and add the
      link; do not build payments into the site.
- [ ] **Referral rules** — who qualifies, reward value, abuse limits. Ticket **#29**.
- [ ] **Legal/privacy wording** — the contact form stores **IP address and user
      agent** and rate-limits by IP. You need a privacy notice that says so, and
      a lawful basis/consent approach for contact messages, newsletter signup
      (#12) and any photo/UGC submission (#28). This is not legal advice; have
      it reviewed if you are unsure.

## 4. Verification I could not run here

- [ ] **Docker smoke test** — `tests/docker_smoke_test.sh` was **not run**
      because Docker is unavailable on this machine. Run it on a machine with
      Docker before relying on the container path:
      `tests/docker_smoke_test.sh`.
- [ ] **Real-browser / device pass** — tests use jsdom, not a real browser. Check
      the public site and admin panel on a phone, Safari and Firefox, including
      the shared navigation (homepage and `/menu`), the Drink of the Day hero,
      the newsletter and reservation forms, the event RSVP form, the content
      editor, the subscriber list, the reservation queue, the event guest list
      and the image uploader (including a real phone photo and a large photo).
- [ ] **PWA install and offline check** — install the app on a real Android and
      iPhone, confirm the manifest icons and standalone window, then load `/`
      and `/menu` offline. The service worker is not exercised by jsdom tests.
- [ ] **Production HTTPS/cookie check** — confirm login works with
      `COOKIE_SECURE=true` and that the session survives a normal navigation.
- [ ] **Real notification test** — once SMTP/WhatsApp exists, submit the contact
      form and confirm delivery, formatting and spam behaviour.
- [ ] **Backup/restore drill on the real server** — the script has tests, but it
      has not been run against production storage.
- [ ] **Load/concurrency sanity check** — SQLite is single-writer by design; the
      app runs one worker. Confirm that matches expected Friday-night traffic.
- [ ] **Accessibility audit with real assistive tech** — ticket **#33** is not
      built; automated checks do not replace a screen-reader pass.
- [ ] **Content proofread by a native Spanish speaker** — the Spanish copy is
      translated but should be reviewed for local Ecuadorian usage.

## 5. Code tickets still to build

These are buildable later; they are **not** blocked by missing accounts or
content (except where noted). They were simply not part of the five-ticket batch.

| # | Ticket | Note |
|---|--------|------|
| 21 | Loyalty program | Needs programme rules. |
| 26 | Live music calendar | After #53; calendar over dated events. |
| 27 | “Perfect Drink” quiz | Frontend only, resolves against `/api/menu`. |
| 29 | Referral program | After #21; needs referral rules. |
| 32 | Dark mode toggle | CSS variables, toggle, persisted choice. |
| 33 | Accessibility pass | Public site and admin panel. |
| 34 | Performance optimizations | App-side work only; nginx caching is deploy work. |
| 35 | Expanded automated testing | Playwright E2E + coverage. |
| 36 | CI/CD rebuild | CI portion buildable; deploy job needs VPS secrets. |
| 51 | Full submission notification | Inbox is done; email/WhatsApp needs credentials. |
| 56 | CSV export / import | Admin export/import with per-row validation. |

Content-dependent code work is in section 3: **#8, #11, #18, #19, #20, #22,
#23, #24, #28, #30**. External-only work is in section 2: **#2, #4, #5, #6, #13,
#37, #40, #47**.

## 6. Decisions I made that you should confirm

- **Contact inbox scope (#15)** — “global admin DM box” was implemented as one
  shared contact-form inbox visible to every admin, not private per-admin
  messages. Confirm that is what you meant.
- **Contact-form fields (#15)** — name, contact and message are required after
  sanitisation; subject is optional; messages are capped at 1,000 characters;
  the `website` honeypot silently accepts and stores nothing.
- **Promo windows (#7)** — weekdays are comma-separated integers with
  `0 = Sunday`; times are bar-local `HH:MM`; blank start/end means all day;
  blank dates mean no bound; an end earlier than the start crosses midnight.
- **Dated events (#53)** — image is a URL, not an upload, because #50 is not
  built; new events reject past dates but edits allow them; the public read
  hides past and switched-off events; the admin read keeps everything.
- **Audit logging (#53)** — dated-event create/update/delete are logged in the
  schedule area as `special_event:<id>`. Inbox actions (read/delete) are **not**
  audited.
- **Shared navigation (#16)** — one `Nav.svelte` renders both headers. The
  homepage uses in-page anchors; `/menu` links back to `/#surf`, `/#party`,
  `/#contact` and `/#visit`, and omits the menu link it is already on.
- **Drink of the Day (#10)** — the owner marks one menu item with
  `is_drink_of_day`; the write path clears every other row. There is no date
  scheduling and no automatic rotation, so “of the day” means “until someone
  changes it”.
- **Generic content (#17)** — sections and items are generic, not menu- or
  package-specific: bilingual title/body, optional price, image **URL**, optional
  date window and an active flag. There is no public layout for these rows yet;
  #8/#19/#20/#22 will decide how they render. Writes are audited as
  `content_section:<id>` / `content_item:<id>`.
- **Newsletter (#12)** — signup requires the consent checkbox and stores the
  timestamp, IP and user agent; the honeypot and per-IP limiter mirror the
  contact form. Duplicate addresses return the same success response and create
  no second row. There is no double opt-in, no delivery and no unsubscribe link
  in an email; the admin switch and CSV export are the whole flow.
- **Reservations (#14)** — a request is always created `pending`; the admin
  confirm/decline/reset actions do not notify the guest. Defaults are 1–20
  guests and today to 90 days ahead. Subscriber and reservation admin actions are
  **not** audited (matching inbox actions); content and menu writes are.
- **Image uploads (#50)** — JPEG, PNG, WebP and GIF up to 10 MB, re-encoded to
  WebP at 1600 px plus a 480 px thumbnail; the original is discarded. Filenames
  are random and served with a one-year immutable cache header. There is no
  public gallery yet (#8), no cropping/editing, and deleting an upload does not
  rewrite content rows that already point at its URL.
- **Event RSVPs (#25)** — free RSVPs only; there is no payment, ticket code,
  capacity limit, waitlist or guest notification. A hidden or past event returns
  404. Deleting an event removes its guest list, and the admin delete is **not**
  audited (matching inbox and reservation actions).
- **PWA (#31)** — the service worker caches the shell, pages, hashed assets and
  the five public API reads; it never caches `/admin` or admin API reads. Bump
  `VERSION` in `frontend/public/sw.js` when the shell changes, and serve
  `/sw.js` with `Cache-Control: no-cache` so a new worker is picked up. Install
  prompts require HTTPS (or localhost).
- **No push** — all commits are local only. Nothing has been pushed to a
  remote.

---

_Last updated after tickets #16, #10, #17, #12 and #14. Keep this file honest:
delete a line when it is actually done, and add one when a new external
dependency appears._
