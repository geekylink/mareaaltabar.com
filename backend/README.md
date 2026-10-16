# Marea Alta — Backend

FastAPI server with SQLite database for managing the party schedule, operating hours, closed days and the drinks menu. Includes a secure admin panel.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy `.env` and adjust values as needed:

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Set to `production` to disable docs and enable secure cookies |
| `SECRET_KEY` | _(auto)_ | Random secret for session signing |
| `DATABASE_PATH` | `./data/marea_alta.db` | Path to SQLite database file |
| `SESSION_TTL_HOURS` | `8` | Session lifetime in hours |
| `COOKIE_SECURE` | `true` (prod) | Set `true` to require HTTPS for cookies |
| `RATE_LIMIT_ATTEMPTS` | `5` | Max login attempts per window |
| `RATE_LIMIT_WINDOW_MINUTES` | `10` | Rate limit window duration |

## Running

```bash
# Development (auto-reload)
uvicorn app.main:app --reload --port 8000

# Production: build the frontend first, then the backend serves it
cd ../frontend && npm run build && cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

When `frontend/dist` exists, the backend serves the site from the same origin at
`/`, so the site and the API that feeds it share a domain (no CORS needed).

## Testing

```bash
pip install pytest httpx
python -m pytest tests/ -v
```

The suite runs against an in-memory database and covers login/session handling,
CSRF enforcement, the admin CRUD API (schedule, closed days and the drinks menu),
the server-rendered homepage and `/menu`, the bilingual admin strings, and
end-to-end propagation of admin edits to the public read endpoints *and* to the
rendered HTML. Tests never touch `data/marea_alta.db`.

## Admin Management

```bash
# Create an admin user
python manage_admin.py create <username> <password>

# List all admins
python manage_admin.py list

# Delete an admin
python manage_admin.py delete <username>

# Reset a password
python manage_admin.py password <username> <new_password>
```

## Admin Panel

Once logged in at `/admin`, you can:

- **Party Schedule** (`/admin/schedule`): one card per weekday holding the party
  title and description in **both English and Spanish**, plus that day's opening
  hours and a "closed" switch. Per-day **Save**, or **Save all days** at the top.
  A colour bar on the left of each field shows whether that language is filled in.
- **Closed Days**: add one-off closures (holidays, private events) with a reason
  in both languages. Reasons save when you click away from the field.
- **Drinks Menu** (`/admin/menu`): one card per category — Beer, Wine, Cocktails,
  and whatever else the bar adds. In each one:

  - **Add item** at the bottom of the card, **Remove** and **↑/↓** on every
    drink, and **Delete category** on the card itself.
  - Click a drink to expand it: names, price, description and **ingredients** in
    both languages. Ingredients are a comma-separated list, which is what the
    cocktails section shows.
  - **Promos** live in a sub-list under the price — an item can carry several
    ("6x $7.00" and "case $12.00"). They save with the item, so the price and
    the offers beneath it can never disagree.
  - **On the menu** hides a drink or a whole section without deleting it. That is
    the reversible move for something sold out; delete is for something gone.
    A hidden drink is invisible on the site but still editable here.

The admin panel is not linked from the public website. It is only accessible by navigating directly to `/admin`.

## API Endpoints

**Read endpoints are public** — the website fetches them with no login. Every
string comes back in **both languages**, so switching language needs no extra
request. The frontend picks the field matching the visitor's language and falls
back to English when a translation is blank.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/schedule` | Public | The whole week: titles, descriptions and hours per day |
| `GET` | `/api/closed-days` | Public | One-off date closures, both languages, today and later |
| `GET` | `/api/menu` | Public | The drinks menu: categories, items and promos, both languages |
| `GET` | `/api/menu/all` | Admin | The same, plus items and categories switched off |
| `GET` | `/` | Public | The site, with the schedule **and the menu** rendered into the HTML |
| `GET` | `/menu` | Public | The drinks menu on its own page, rendered into the HTML |

**Write endpoints require an admin session and a CSRF token.**

| Method | Path | Description |
|---|---|---|
| `PUT` | `/api/schedule/{day}` | Save a day's titles, descriptions **and** hours together |
| `POST` | `/api/closed-days` | Add a closure (today or later) |
| `PATCH` | `/api/closed-days/{id}` | Correct a closure's wording later |
| `DELETE` | `/api/closed-days/{id}` | Remove a closure |
| `POST` | `/api/menu/categories` | Add a section (Beer, Wine, Food…) |
| `PATCH` | `/api/menu/categories/{id}` | Rename it, retitle it, move it, or switch it off |
| `DELETE` | `/api/menu/categories/{id}` | Remove a section and every drink in it |
| `POST` | `/api/menu/items` | Add a drink, with its promos |
| `PUT` | `/api/menu/items/{id}` | Save a drink: copy, price, ingredients, promos, availability, category |
| `DELETE` | `/api/menu/items/{id}` | Take a drink off the menu |

### How the menu is stored

Every visitor-facing string is bilingual (`name_en`/`name_es`,
`description_en`/`description_es`, `ingredients_en`/`ingredients_es`), so
`pick()` falls back to English and a half-translated menu still renders.

Three details are deliberate:

- **A price is the headline figure only.** `1.50 (6x $7.00)` from
  `docs/bar_menu.md` becomes price `1.50` plus a promo row. Several offers can sit
  under one drink, and the admin edits them in the same save as the price.
- **`price` is text, not a number.** It is a displayed price, never arithmetic, so
  it is stored exactly as typed — no float rounding, no locale surprises.
  Ticket #49's `offers.price` will want a numeric column when it lands.
- **`/api/menu` hides what has been switched off; `/api/menu/all` does not.**
  The public read must not publish a sold-out drink, but the panel has to be able
  to see it, or it could never be switched back on. The admin page loads from
  `/api/menu/all`.

Reads send `Cache-Control: no-cache` so admin edits appear without visitors
having to hard-refresh.

**Closures are only published from today onward.** `load_closed_days()` filters
on `date >= bar_today()[1]`, so a closure stops being returned the day after it
happens instead of rendering on the site for ever, and `ClosedDayCreate` refuses
the same dates using the same clock — one clock decides both what can be created
and what is published. It is the **bar's** date, not the server's: they differ by
five hours, and a UTC server between 19:00 and midnight would otherwise reject
the bar's own today.

Past rows stay in the `closed_days` table, but since the panel loads its
closed-days list from the same public endpoint, they also disappear from the
admin list. Editing or removing a closure that has already passed is no longer
possible from the panel; the rows are inert and can be deleted from the database
whenever is convenient.

Times are stored 24-hour (`HH:MM`) so the admin panel's `<input type="time">`
can populate them; the frontend formats them per locale.

## Server-Rendered Homepage and Menu

`/`, `/index.html` and `/menu` are **rendered**, not served off disk. `app/ssr.py`
reads `frontend/dist/index.html` and `frontend/dist/menu.html` and injects:

- the week's hours, party titles and closure notices — and, on the homepage, the
  drinks menu — as plain HTML inside `<div id="app">`, so a crawler sees them
  without running any JavaScript, and
- the same payload as `window.__MAREA_ALTA_DATA__`, which the SPA uses for its
  first paint instead of fetching.

The rendered block is replaced when the app mounts, so visitors see exactly what
they saw before; nothing is hydrated. `frontend/src/main.js` clears the mount
point first, since Svelte's `mount()` appends rather than replaces.

Why at request time and not at build time: the hours are editable from the admin
panel, so a build-time render would put last week's opening hours into the HTML
and nothing would notice until the next deploy.

| Route | Behaviour |
|---|---|
| `GET /` | English (the default), or `?lang=es` for Spanish, which also sets `<html lang>` |
| `GET /index.html` | The same, so an old inbound link does not fall through to the raw shell |
| `GET /menu` | The drinks menu alone, on its own document — the shareable URL |
| `GET /menu.html` | The same, so an old inbound link does not fall through to the raw shell |

Anything else — hashed assets, the favicon — is still served by the static mount.
`Cache-Control: no-cache`, for the same reason the JSON reads use it. If
rendering fails for any reason the un-injected shell is served and the error is
logged, rather than the homepage going down.

`app/ssr.py` and `app/routers/api.py` share one set of loaders (`load_schedule`,
`load_closed_days`, `load_menu`, `day_payload`), so the JSON and the HTML cannot
describe different weeks, different closure notices or different menus. A closure
dated today closes today's row in the rendered HTML for the same reason it closes
it in the SPA — otherwise the page would promise a party on a public holiday and
visibly change the moment the app mounted over it. `app/public_i18n.py` holds the
handful of labels the rendered blocks need; the rest of the site's wording lives in
`frontend/src/content/*.js`, and a test in the frontend suite fails if the shared
strings drift apart.

**nginx must proxy `/` and `/menu` here.** Serving the built HTML straight off
disk skips the rendering and puts the schedule and the menu back out of reach of
crawlers. `/assets/` can still be served from disk.

This is also where ticket #5's `openingHoursSpecification` and ticket #49's menu
JSON-LD belong.

## Bilingual Admin Panel

The admin pages are available in English and Spanish. Language follows the
choice made on the public site (shared `localStorage`, same origin), and each
page has an **EN / ES** toggle that switches instantly without a reload.

To add a language, extend `STRINGS` in `app/admin_i18n.py` and add the code to
`SUPPORTED` — no template changes needed.

## Migrations

SQLite cannot rename or drop columns cheaply, so schema changes are applied as
explicit statements in `app/migrate.py`, run automatically at startup and
covered by `tests/test_migrations.py`.

The bilingual upgrade is non-destructive: existing single-language content
becomes English, Spanish is seeded with the same text so nothing renders blank
before a human translates it, and legacy `4:00 PM` times are normalised to
`16:00` so the time inputs populate correctly.

`migrate_menu_schema` covers the one thing `create_all` will not do: it creates
missing tables but never alters an existing one, so a database that already has a
`menu_items` table gets `ingredients_*` and `is_available` added here, with
defaults that leave the drinks that are already in it intact.

**Known gap:** the closed-days migration copies `reason` into `reason_en` /
`reason_es` but leaves the old column in place, and it was declared `NOT NULL`
without a default. On any database created before that migration, adding a
closed day fails with `NOT NULL constraint failed: closed_days.reason`. A fresh
database is unaffected. SQLite cannot drop a column before 3.35, so the fix is
either a table rebuild in `migrate.py` or a nullable redefinition — it is not
covered by the migration tests, which build their schema from the models.

## Security

- **Password hashing**: bcrypt via passlib
- **Sessions**: Server-side in SQLite, cryptographically random tokens, 8-hour expiry
- **Cookies**: HttpOnly, SameSite=Lax, Secure in production
- **CSRF protection**: Double-submit cookie pattern on all state-changing requests
- **Rate limiting**: 5 *failed* login attempts per 10 minutes per IP (successes don't count, so regular use never locks anyone out)
- **Authorization**: Read endpoints are public; all writes and the entire admin panel require a session
- **Security headers**: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- **SQL injection**: SQLAlchemy 2.0 parameterized queries
- **XSS**: Jinja2 auto-escaping, no inline scripts

## Database Schema

### `admins`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `username` | TEXT UNIQUE | Required |
| `password_hash` | TEXT | bcrypt hash |
| `created_at` | DATETIME | Auto-set |

### `sessions`
| Column | Type | Notes |
|---|---|---|
| `token` | TEXT PK | 64-char hex |
| `admin_id` | INTEGER FK | → admins.id |
| `csrf_token` | TEXT | 64-char hex |
| `created_at` | DATETIME | Auto-set |
| `expires_at` | DATETIME | Required |

### `events`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `day` | INTEGER UNIQUE | 0=Sun ... 6=Sat |
| `title_en` / `title_es` | TEXT | Party name in both languages |
| `note_en` / `note_es` | TEXT | Description in both languages |
| `created_at` / `updated_at` | DATETIME | Auto-set |

### `hours`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `day` | INTEGER UNIQUE | 0=Sun ... 6=Sat |
| `open_time` / `close_time` | TEXT | 24-hour `HH:MM` |
| `is_closed` | BOOLEAN | 0 or 1 |
| `created_at` / `updated_at` | DATETIME | Auto-set |

### `closed_days`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `date` | TEXT UNIQUE | YYYY-MM-DD format |
| `reason_en` / `reason_es` | TEXT | Reason in both languages |
| `created_at` / `updated_at` | DATETIME | Auto-set |

### `menu_categories`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `slug` | TEXT UNIQUE | Anchor id on the menu page, e.g. `cocteles` |
| `name_en` / `name_es` | TEXT | Section heading in both languages |
| `sort_order` | INTEGER | Menu order, set by the ↑/↓ buttons |
| `is_available` | BOOLEAN | Cleared hides the section without deleting it |
| `created_at` / `updated_at` | DATETIME | Auto-set |

### `menu_items`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `category_id` | INTEGER FK | → menu_categories.id, cascades on delete |
| `name_en` / `name_es` | TEXT | The drink in both languages |
| `description_en` / `description_es` | TEXT | Optional flavour text |
| `ingredients_en` / `ingredients_es` | TEXT | Comma-separated; what cocktails show |
| `price` | TEXT | Headline price as typed, e.g. `2.50` |
| `sort_order` | INTEGER | Order within the category |
| `is_available` | BOOLEAN | Cleared hides the drink without deleting it |
| `created_at` / `updated_at` | DATETIME | Auto-set |

### `menu_item_promos`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `menu_item_id` | INTEGER FK | → menu_items.id, cascades on delete |
| `label_en` / `label_es` | TEXT | e.g. `6x $7.00` / `6 por $7.00` |
| `sort_order` | INTEGER | Several promos per drink, in order |
| `created_at` / `updated_at` | DATETIME | Auto-set |
