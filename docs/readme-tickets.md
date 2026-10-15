# README-tickets.md

> **Companion to the Marea Alta Surf Bar website.** This document covers a complete set of improvements to drive visitors to the bar and its social media. The site currently focuses on surf conditions and party schedule, but the primary business is **drinks** — beer, wine, liquor, and cocktails. These tickets address that gap and more.

**Legend**
- **Impact:** 🔴 Critical · 🟠 High · 🟡 Medium · ⚪ Low
- **Effort:** 🟢 S (<1 day) · 🟡 M (1–3 days) · 🔴 L (1+ week)

---

Project manager note:
* Finished tickets should be moved to "Completed Tickets" section and removed from "TO-DO"
* Ticket should be marked completed in "Summary Table"
* Cross out ticket number in "Suggested Sprint Order"

---

## Table of Contents

- [Tier 1 — Quick Wins (High Impact, Low Effort)](#tier-1--quick-wins-high-impact-low-effort)
  - [1. Add a drinks menu page](#1-add-a-drinks-menu-page)
  - [2. Add WhatsApp floating button](#2-add-whatsapp-floating-button)
  - [3. Add Open Graph / social preview tags](#3-add-open-graph--social-preview-tags)
  - [4. Add analytics (Plausible or Google Analytics)](#4-add-analytics-plausible-or-google-analytics)
  - [5. Add structured data (Schema.org LocalBusiness)](#5-add-structured-data-schemalocalbusiness)
  - [6. Display phone number and address prominently](#6-display-phone-number-and-address-prominently)
  - [7. Add happy hour / daily promos section](#7-add-happy-hour--daily-promos-section)
  - [8. Add photo gallery of drinks and atmosphere](#8-add-photo-gallery-of-drinks-and-atmosphere)
  - [9. Add proper favicon and app icons](#9-add-proper-favicon-and-app-icons)
  - [10. Add a "Drink of the Day" hero banner](#10-add-a-drink-of-the-day-hero-banner)
- [Tier 2 — High Value (Medium Effort)](#tier-2--high-value-medium-effort)
  - [11. Add food menu section](#11-add-food-menu-section)
  - [12. Add email capture / newsletter signup](#12-add-email-capture--newsletter-signup)
  - [13. Embed Instagram feed](#13-embed-instagram-feed)
  - [14. Add reservation / table booking system](#14-add-reservation--table-booking-system)
  - [15. Add contact form](#15-add-contact-form)
  - [16. Create separate menu page (multi-page structure)](#16-create-separate-menu-page-multi-page-structure)
  - [17. Add CMS for menu management](#17-add-cms-for-menu-management)
  - [18. Add drink pricing and descriptions](#18-add-drink-pricing-and-descriptions)
  - [19. Add "About Us" section](#19-add-about-us-section)
  - [20. Add private events / group booking info](#20-add-private-events--group-booking-info)
- [Tier 3 — Growth & Engagement](#tier-3--growth--engagement)
  - [21. Add loyalty program](#21-add-loyalty-program)
  - [22. Add birthday / package deals](#22-add-birthday--package-deal)
  - [23. Add merch / store section](#23-add-merch--store-section)
  - [24. Add blog / news section](#24-add-blog--news-section)
  - [25. Add event ticketing / RSVP](#25-add-event-ticketing--rsvp)
  - [26. Add live music calendar integration](#26-add-live-music-calendar-integration)
  - [27. Add "Perfect Drink" quiz / recommendation](#27-add-perfect-drink-quiz--recommendation)
  - [28. Add user-generated content (photo contest)](#28-add-user-generated-content-photo-contest)
  - [29. Add referral program](#29-add-referral-program)
  - [30. Add "Drinks We're Known For" signature section](#30-add-drinks-were-known-for-signature-section)
- [Tier 4 — Polish & Infrastructure](#tier-4--polish--infrastructure)
  - [31. Add PWA support](#31-add-pwa-support)
  - [32. Add dark mode toggle](#32-add-dark-mode-toggle)
  - [33. Accessibility pass](#33-accessibility-pass)
  - [34. Performance optimizations](#34-performance-optimizations)
  - [35. Add automated testing](#35-add-automated-testing)
  - [36. CI/CD improvements](#36-cicd-improvements)
  - [37. Add error tracking (Sentry)](#37-add-error-tracking-sentry)
  - [38. Add backup strategy](#38-add-backup-strategy)
  - [39. Add uptime monitoring](#39-add-uptime-monitoring)
  - [40. Add CDN for static assets](#40-add-cdn-for-static-assets)
- [Summary Table](#summary-table)
- [Suggested Sprint Order](#suggested-sprint-order)
- [Completed Tickets](#completed-tickets)

---

# TO-DO

## Tier 1 — Quick Wins (High Impact, Low Effort)
*The fastest path to more visitors. Most of these are under a day each and directly drive foot traffic.*

### 1. Add a drinks menu page
**Impact:** 🔴 · **Effort:** 🟢 · **Category:** Functionality

The single biggest gap. The bar sells beer, wine, liquor, and cocktails, but the site has zero drink information. Create a dedicated menu section (or page) listing all drinks with names, descriptions, and prices. Organize by category: Beers, Wines, Spirits, Cocktails, Non-Alcoholic. Since stock rotates regularly, structure the data so items can be easily added/removed. Include a "Today's Specials" subsection for daily/weekend promos.

**Files:** `src/lib/data.js` (new `MENU` array), `src/content/en.js` + `src/content/es.js` (menu labels), new `src/lib/Menu.svelte`, `src/App.svelte` (add section)

---

### 2. Add WhatsApp floating button
**Impact:** 🔴 · **Effort:** 🟢 · **Category:** Growth

WhatsApp is the primary communication channel in Ecuador. Add a floating action button (bottom-right on mobile, bottom-left on desktop) that opens a WhatsApp chat with the bar's number. Pre-fill the message with "Hi! I saw your website and have a question." This converts casual visitors into real-time conversations. Use the `wa.me` short link format.

**Files:** `src/App.svelte` (add floating button component), `src/lib/data.js` (add `whatsapp` field to `BAR`)

---

### 3. Add Open Graph / social preview tags
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Growth

When someone shares the site link in WhatsApp, Instagram, or Facebook, it currently shows a bare URL. Add `og:title`, `og:description`, `og:image`, and `og:type` meta tags. Create a compelling brand card image (1200x630px) featuring the bar's name, a cocktail, and the Montañita vibe. This makes shared links look professional and drives clicks.

**Files:** `index.html` (add OG meta tags), new `static/og-image.png` (brand card image)

---

### 4. Add analytics (Plausible or Google Analytics)
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** DevOps

Currently flying blind — no idea how many visitors come, where they find the site, or what they click. Add Plausible (privacy-friendly, lightweight) or Google Analytics 4. Track page views, referral sources, and outbound link clicks (especially social media and WhatsApp). This data is essential for measuring whether improvements actually drive traffic.

**Files:** `index.html` (add analytics script)

---

### 5. Add structured data (Schema.org LocalBusiness)
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** SEO

Add JSON-LD structured data marking the site as a `BarOrPub` with name, address, phone, opening hours, and servesCuisine. This helps Google show the bar in local search results, Google Maps, and the knowledge panel. Include `geo` coordinates for Montañita. This is the single highest-impact SEO change for a local business.

**Files:** `index.html` (add `<script type="application/ld+json">` block)

---

### 6. Display phone number and address prominently
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** UX

The "Find us" section has a map link but no visible phone number or street address. Add the phone number (clickable `tel:` link) and full address in the Visit section and footer. Tourists looking for a bar need to know where it is and whether to call ahead. Also add a "Call now" button on mobile.

**Files:** `src/lib/data.js` (add `phone`, `address` to `BAR`), `src/App.svelte` (Visit section), `src/content/en.js` + `src/content/es.js`

---

### 7. Add happy hour / daily promos section
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Functionality

The bar runs promos on different days, but the site doesn't mention them. Add a "Promos" section (or integrate into the Party section) showing daily drink specials. Structure it like the existing EVENTS array — one entry per day with time range and description. Example: "Tuesday: 2x1 Cocktails 5-7pm", "Weekend: $3 Beers until 8pm". Update weekly.

**Files:** `src/lib/data.js` (add `PROMOS` array), `src/content/en.js` + `src/content/es.js` (promo labels), `src/App.svelte` (add section or integrate into Party)

---

### 8. Add photo gallery of drinks and atmosphere
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Design

Bars sell on vibes. The site has zero photos. Add a gallery section with high-quality images of: signature cocktails, the bar interior, the crowd at night, the beach view, and the surf. Use a simple grid or carousel. Optimize images for web (WebP, lazy loading). This is the most persuasive content for someone deciding where to go.

**Files:** new `src/lib/Gallery.svelte`, `src/App.svelte` (add section), new `static/gallery/` directory with optimized images

---

### 9. Add proper favicon and app icons
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Design

The current favicon is an emoji SVG data URI. Create a proper branded favicon (a wave or cocktail glass icon) in multiple sizes: 16x16, 32x32, 180x180 (Apple touch icon), 192x192 and 512x512 (PWA icons). This makes the site look professional in browser tabs, bookmarks, and when saved to a phone home screen.

**Files:** `index.html` (update favicon links), new `static/icons/` directory with favicon files

---

### 10. Add a "Drink of the Day" hero banner
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Engagement

Rotate a featured drink in the hero section or just below it. Shows the bar's personality and gives people a reason to come today. Include the drink name, a one-line description, and the price. Store in data.js and update daily. This also gives social media content ideas — post the drink of the day on Instagram.

**Files:** `src/lib/data.js` (add `DRINK_OF_DAY` object), `src/App.svelte` (add banner below hero), `src/content/en.js` + `src/content/es.js`

---

## Tier 2 — High Value (Medium Effort)
*Bigger projects that unlock new revenue streams, improve conversions, or reduce operational friction.*

### 11. Add food menu section
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Functionality

If the bar serves food (snacks, ceviches, burgers, etc.), add a food menu section alongside the drinks menu. Even a small food menu increases average visit duration and spend. Structure like the drinks menu with categories and pricing. If food is minimal, at least list available snacks.

**Files:** `src/lib/data.js` (add `FOOD_MENU` array), new `src/lib/FoodMenu.svelte`, `src/App.svelte` (add section)

---

### 12. Add email capture / newsletter signup
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Growth

Build an email list of visitors who want to hear about events, promos, and new drinks. Add a simple signup form (footer or a small pop-up after 10 seconds). Store emails in a free service like Mailchimp, Buttondown, or a simple Google Sheet via a form action. Send a monthly "What's on at Marea Alta" email with upcoming events and drink specials.

**Files:** new `src/lib/Newsletter.svelte`, `src/App.svelte` (add to footer or as pop-up), `src/lib/data.js` (add newsletter endpoint URL)

---

### 13. Embed Instagram feed
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Social Media

The site links to Instagram but doesn't show any content. Embed a live Instagram feed (using a free tool like Elfsight, SnapWidget, or the Instagram Basic Display API) showing the latest 6-9 posts. This keeps the site fresh without manual updates and proves the bar is active. Place it in a "Follow us" section or the gallery.

**Files:** new `src/lib/InstagramFeed.svelte`, `src/App.svelte` (add section), `index.html` (add Instagram widget script if needed)

---

### 14. Add reservation / table booking system
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Functionality

Allow visitors to book a table or reserve a spot for events. For a simple implementation, use a WhatsApp deep link with a pre-filled message including date, time, and party size. For a more advanced system, integrate with a free tool like Calendly or OpenTable. This is especially important for weekends and events when the bar fills up.

**Files:** new `src/lib/Reservation.svelte`, `src/App.svelte` (add section or button), `src/lib/data.js` (add reservation config)

---

### 15. Add contact form
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Functionality

A simple contact form for general inquiries, private event questions, or feedback. Can be a static form that opens the user's email client with a pre-filled message, or a more advanced setup with a backend endpoint. Include fields for name, email, subject, and message. This gives non-WhatsApp users a way to reach the bar.

**Files:** new `src/lib/ContactForm.svelte`, `src/App.svelte` (add section)

---

### 16. Create separate menu page (multi-page structure)
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Architecture

The site is currently a single-page app. As content grows (menu, gallery, about, contact), it becomes unwieldy. Add client-side routing with SvelteKit or a simple hash-based router. Create separate pages: `/menu`, `/gallery`, `/about`, `/contact`. This improves SEO (each page can have its own meta tags), makes the site easier to navigate, and allows deep-linking to specific sections.

**Files:** new `src/lib/router.js` or migrate to SvelteKit, new page components, update `src/App.svelte`

---

### 17. Add CMS for menu management
**Impact:** 🟠 · **Effort:** 🔴 · **Category:** Operations

Currently, updating the menu requires editing code and redeploying. Add a headless CMS (Sanity, Contentful, or Strapi) or a simple JSON-based CMS where the bar owner can add/remove drinks, update prices, and post new promos without touching code. This is essential for a menu that changes regularly. Pair with a simple admin dashboard.

**Files:** new CMS integration, new admin dashboard route, update `src/lib/data.js` to fetch from CMS

---

### 18. Add drink pricing and descriptions
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Functionality

Even before a full menu page, add pricing to any drink mentions. When the menu is built, include detailed descriptions for signature cocktails (ingredients, flavor profile, inspiration). This helps visitors decide what to order and positions the bar as a quality cocktail destination, not just a beach bar.

**Files:** `src/lib/data.js` (menu items with `price` and `description` fields), `src/content/en.js` + `src/content/es.js`

---

### 19. Add "About Us" section
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Content

Tell the bar's story. When was it founded? What makes it special? Why "Marea Alta" (high tide)? Include photos of the owners, the building's history, and the Montañita surf culture connection. This builds emotional connection with visitors and differentiates from other bars. Keep it authentic and fun — this is a surf bar, not a corporate website.

**Files:** new `src/lib/About.svelte`, `src/App.svelte` (add section), `src/content/en.js` + `src/content/es.js` (about text)

---

### 20. Add private events / group booking info
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Revenue

Many bars earn significant revenue from private events (birthdays, bachelor parties, surf competitions). Add a section describing private event offerings: capacity, packages, pricing, and how to book. Include a photo of a past event. This captures high-value bookings that currently might go to competitors.

**Files:** new `src/lib/Events.svelte`, `src/App.svelte` (add section), `src/content/en.js` + `src/content/es.js`

---

## Tier 3 — Growth & Engagement
*Features that build community, increase repeat visits, and turn visitors into regulars.*

### 21. Add loyalty program
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Retention

Reward repeat visitors. Simple version: a digital punch card (buy 9 drinks, get the 10th free) tracked via a QR code or phone number. More advanced: a points system with a free tool like Stamp Me or Loyverse. Promote it on the site with a "Join our loyalty program" section. This directly increases repeat visits.

**Files:** new `src/lib/Loyalty.svelte`, `src/App.svelte` (add section), `src/lib/data.js` (loyalty program details)

---

### 22. Add birthday / package deals
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** Revenue

Birthdays are huge in Montañita's party scene. Create package deals: "Birthday Package: 1 bottle of liquor + 6 mixers + a cocktail for the birthday person + a song." List 2-3 tiers with pricing. Add a "Book your birthday" CTA that opens WhatsApp with pre-filled details. This captures a high-value market segment.

**Files:** `src/lib/data.js` (add `PACKAGES` array), new `src/lib/Packages.svelte`, `src/App.svelte` (add section)

---

### 23. Add merch / store section
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Revenue

Sell branded merchandise: t-shirts, hats, stickers, koozies. Even a small merch section creates an additional revenue stream and turns visitors into walking advertisements. Use a simple print-on-demand service (Printful, Printify) or list items with a "Order via WhatsApp" button. Include photos of the merch.

**Files:** new `src/lib/Merch.svelte`, `src/App.svelte` (add section), `src/lib/data.js` (merch items)

---

### 24. Add blog / news section
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** SEO / Content

A blog drives organic traffic from search. Post about: upcoming events, new drink recipes, surf conditions, Montañita travel tips, and local stories. Even one post per month improves SEO significantly. Use a simple static site generator or a headless CMS. Share each post on social media.

**Files:** new `src/lib/Blog.svelte`, new `src/lib/BlogPost.svelte`, `src/App.svelte` (add section), new `src/content/posts/` directory

---

### 25. Add event ticketing / RSVP
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Functionality

For big events (live music, themed parties, surf competitions), allow online RSVP or ticket purchase. Use a free tool like Eventbrite, Ticket Tailor, or a simple Google Form. Show upcoming events with a "Get tickets" button. This helps the bar gauge attendance and reduces no-shows.

**Files:** `src/lib/data.js` (add `UPCOMING_EVENTS` array with ticket links), `src/App.svelte` (add to Party section or new Events section)

---

### 26. Add live music calendar integration
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Functionality

The party schedule shows weekly events, but live music nights deserve more detail. Add a dedicated calendar view showing the month's events with artist names, genres, and set times. Integrate with Google Calendar or Bandsintown for automatic updates. Include artist photos and links to their social media.

**Files:** new `src/lib/Calendar.svelte`, `src/App.svelte` (add section), `src/lib/data.js` (detailed event data)

---

### 27. Add "Perfect Drink" quiz / recommendation
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Engagement

A fun interactive feature: "What should you drink tonight?" Ask 3-4 questions (mood, sweet vs. strong, beer vs. cocktail) and recommend a signature drink. This is highly shareable on social media, increases time on site, and helps visitors discover new drinks. Keep it simple and fun.

**Files:** new `src/lib/Quiz.svelte`, `src/App.svelte` (add section or link from hero), `src/lib/data.js` (quiz logic and drink mappings)

---

### 28. Add user-generated content (photo contest)
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Social Media

Run a monthly photo contest: visitors post their best photo at the bar with a hashtag (#MareaAltaNights), and the winner gets a free bottle or bar tab. Display the best photos on the site (with permission). This generates free social media content, increases engagement, and gives people a reason to visit and post.

**Files:** new `src/lib/Contest.svelte`, `src/App.svelte` (add section), `src/lib/data.js` (contest rules and hashtag)

---

### 29. Add referral program
**Impact:** 🟡 · **Effort:** 🟡 · **Category:** Growth

"Bring a friend, both get a drink." Create a simple referral system: give each regular a unique code or QR code, and when a new visitor mentions it, both get a reward. Track with a simple spreadsheet or a free tool. Promote it on the site and in the bar. Word-of-mouth is the strongest marketing in a small town like Montañita.

**Files:** new `src/lib/Referral.svelte`, `src/App.svelte` (add section), `src/lib/data.js` (referral program details)

---

### 30. Add "Drinks We're Known For" signature section
**Impact:** 🟡 · **Effort:** 🟢 · **Category:** Content

Highlight 3-5 signature drinks that make the bar unique. Include beautiful photos, detailed descriptions, and the story behind each one. This gives visitors a reason to come try something they can't get elsewhere. Rotate seasonally. This content is also perfect for social media posts.

**Files:** `src/lib/data.js` (add `SIGNATURE_DRINKS` array), new `src/lib/Signature.svelte`, `src/App.svelte` (add section)

---

## Tier 4 — Polish & Infrastructure
*Technical improvements that make the site faster, more reliable, and easier to maintain.*

### 31. Add PWA support
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** UX / Growth

Make the site installable as a Progressive Web App on phones. Add a web app manifest, service worker for offline caching, and an install prompt. Visitors can add the bar's icon to their home screen and tap it like an app. This dramatically increases repeat visits — the single highest-leverage retention change. Requires HTTPS (GitHub Pages provides this).

**Files:** new `static/manifest.json`, new `static/sw.js` (service worker), `index.html` (add manifest link), `src/App.svelte` (install prompt logic)

---

### 32. Add dark mode toggle
**Impact:** ⚪ · **Effort:** 🟢 · **Category:** Design

The site already uses a dark color palette for the surf section. Add a toggle to switch between light and dark modes, persisted in localStorage. Respect `prefers-color-scheme` by default. This is a nice-to-have that improves usability for night-time browsing (when people are deciding where to go out).

**Files:** `src/app.css` (add dark mode variables), `src/App.svelte` (add toggle button), `src/lib/i18n.js` (add dark mode preference)

---

### 33. Accessibility pass
**Impact:** ⚪ · **Effort:** 🟡 · **Category:** Design

Conduct an accessibility audit: ensure all images have alt text, color contrast meets WCAG AA, all interactive elements are keyboard-navigable, ARIA labels are correct, and the site works with screen readers. The current site has some good practices (focus-visible rings, aria-labels) but needs a thorough pass. This broadens the audience and is the right thing to do.

**Files:** all `.svelte` files, `src/app.css`

---

### 34. Performance optimizations
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** Efficiency

Optimize for the slow mobile connections common on Ecuador's coast: lazy-load images, minify CSS/JS, preload critical resources, use a CDN for static assets, and implement proper caching headers. Target a Lighthouse performance score of 90+. Compress all images to WebP. Consider using `vite-plugin-image-optimizer` or similar.

**Files:** `vite.config.js` (add optimization plugins), `index.html` (add resource hints), all image assets

---

### 35. Add automated testing
**Impact:** 🟠 · **Effort:** 🔴 · **Category:** Quality

Nothing is tested. Add: Vitest for unit tests (i18n, data integrity, utility functions), and Playwright for end-to-end tests (page loads, language toggle works, menu renders, links are valid). Without tests, every change risks breaking the site silently. Start with critical paths: the menu page, language toggle, and external links.

**Files:** new `tests/` directory, `vitest.config.js`, `playwright.config.js`, `package.json` (add test scripts)

---

### 36. CI/CD improvements
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** DevOps

The current GitHub Actions workflow only builds and deploys. Add: linting (ESLint), type checking (svelte-check), automated tests, and a build size check. Add a staging environment for testing before production. Require all checks to pass before deployment. This prevents broken deploys during peak hours (Friday night in Montañita).

**Files:** `.github/workflows/deploy.yml` (add lint/test steps), new `.github/workflows/ci.yml`

---

### 37. Add error tracking (Sentry)
**Impact:** 🟠 · **Effort:** 🟡 · **Category:** DevOps

When something breaks, you need to know immediately. Add Sentry (free tier) for both frontend and backend error tracking. Tag errors with the route and user action. Set up alerts for critical errors. This is especially important once the site drives real revenue — a broken menu page on a Friday night costs money.

**Files:** `src/main.js` (add Sentry init), `package.json` (add Sentry dependency), `index.html` (add Sentry config)

---

### 38. Add backup strategy
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** DevOps

If using a CMS or database, implement automated backups. For a static site, ensure the Git repository is the source of truth and is backed up. If using a headless CMS, export content regularly. Add a simple backup script and document the restore process. Test the restore path at least once.

**Files:** new `scripts/backup.sh`, `README.md` (document backup/restore process)

---

### 39. Add uptime monitoring
**Impact:** 🟠 · **Effort:** 🟢 · **Category:** DevOps

Use a free uptime monitor (UptimeRobot, Better Stack, or GitHub Actions cron) to check the site is up every 5 minutes. Get alerted via email or WhatsApp if it goes down. A dead website during high season costs real money. This is cheap insurance.

**Files:** new `.github/workflows/uptime.yml` (optional self-hosted), or configure external service

---

### 40. Add CDN for static assets
**Impact:** ⚪ · **Effort:** 🟡 · **Category:** Efficiency

Put Cloudflare (free tier) in front of the site for faster global access, DDoS protection, and automatic caching. This is especially important for image-heavy pages (gallery, menu). GitHub Pages already uses a CDN, but Cloudflare adds extra performance and security. Only worth doing once traffic is meaningful.

**Files:** DNS configuration, Cloudflare dashboard setup

---

## Summary Table

(✅ completed, ⏳ in progress, 🚫 blocked, 🧪 waiting testing, ❌ wontfix, blank for not started)

| Status | # | Ticket | Impact | Effort | Category |
|:------:|---|--------|:------:|:------:|----------|
| | 1 | Add a drinks menu page | 🔴 | 🟢 | Functionality |
| | 2 | Add WhatsApp floating button | 🔴 | 🟢 | Growth |
| | 3 | Add Open Graph / social preview tags | 🟠 | 🟢 | Growth |
| | 4 | Add analytics (Plausible or GA) | 🟠 | 🟢 | DevOps |
| | 5 | Add structured data (Schema.org) | 🟠 | 🟢 | SEO |
| | 6 | Display phone number and address | 🟠 | 🟢 | UX |
| | 7 | Add happy hour / daily promos | 🟠 | 🟢 | Functionality |
| | 8 | Add photo gallery | 🟠 | 🟢 | Design |
| | 9 | Add proper favicon and app icons | 🟡 | 🟢 | Design |
| | 10 | Add "Drink of the Day" banner | 🟡 | 🟢 | Engagement |
| | 11 | Add food menu section | 🟠 | 🟡 | Functionality |
| | 12 | Add email capture / newsletter | 🟠 | 🟡 | Growth |
| | 13 | Embed Instagram feed | 🟠 | 🟡 | Social Media |
| | 14 | Add reservation / booking system | 🟠 | 🟡 | Functionality |
| | 15 | Add contact form | 🟡 | 🟡 | Functionality |
| | 16 | Create separate menu page | 🟠 | 🟡 | Architecture |
| | 17 | Add CMS for menu management | 🟠 | 🔴 | Operations |
| | 18 | Add drink pricing and descriptions | 🟠 | 🟢 | Functionality |
| | 19 | Add "About Us" section | 🟡 | 🟢 | Content |
| | 20 | Add private events / group booking | 🟡 | 🟡 | Revenue |
| | 21 | Add loyalty program | 🟠 | 🟡 | Retention |
| | 22 | Add birthday / package deals | 🟠 | 🟢 | Revenue |
| | 23 | Add merch / store section | 🟡 | 🟡 | Revenue |
| | 24 | Add blog / news section | 🟡 | 🟡 | SEO / Content |
| | 25 | Add event ticketing / RSVP | 🟡 | 🟡 | Functionality |
| | 26 | Add live music calendar | 🟡 | 🟡 | Functionality |
| | 27 | Add "Perfect Drink" quiz | 🟡 | 🟡 | Engagement |
| | 28 | Add photo contest / UGC | 🟡 | 🟡 | Social Media |
| | 29 | Add referral program | 🟡 | 🟡 | Growth |
| | 30 | Add signature drinks section | 🟡 | 🟢 | Content |
| | 31 | Add PWA support | 🟠 | 🟡 | UX / Growth |
| | 32 | Add dark mode toggle | ⚪ | 🟢 | Design |
| | 33 | Accessibility pass | ⚪ | 🟡 | Design |
| | 34 | Performance optimizations | 🟠 | 🟡 | Efficiency |
| | 35 | Add automated testing | 🟠 | 🔴 | Quality |
| | 36 | CI/CD improvements | 🟠 | 🟡 | DevOps |
| | 37 | Add error tracking (Sentry) | 🟠 | 🟡 | DevOps |
| | 38 | Add backup strategy | 🟠 | 🟢 | DevOps |
| | 39 | Add uptime monitoring | 🟠 | 🟢 | DevOps |
| | 40 | Add CDN for static assets | ⚪ | 🟡 | Efficiency |

---

## Suggested Sprint Order

**Sprint 0 — "Get found" (1 week)**
Tickets 1, 2, 3, 4, 5, 6, 7, 9.
*Goal: Make the bar discoverable and give visitors a reason to come today.*

**Sprint 1 — "Show the drinks" (1-2 weeks)**
Tickets 8, 10, 11, 18, 19, 30.
*Goal: Build out the visual and content foundation — photos, menu, signature drinks.*

**Sprint 2 — "Convert visitors" (2 weeks)**
Tickets 12, 13, 14, 15, 20, 22.
*Goal: Turn website visitors into real-world customers with booking, packages, and contact options.*

**Sprint 3 — "Build loyalty" (2-3 weeks)**
Tickets 16, 17, 21, 23, 24, 25, 26, 27, 28, 29.
*Goal: Create repeat visitors and community engagement through loyalty, events, and content.*

**Sprint 4 — "Harden and scale" (2-3 weeks)**
Tickets 31, 33, 34, 35, 36, 37, 38, 39, 40.
*Goal: Make the site fast, reliable, and maintainable as traffic grows.*

**Later** — Ticket 32 (dark mode) and any remaining nice-to-haves.

---

# Completed Tickets

*(No tickets completed yet. Move finished tickets here and update the Summary Table.)*
