# Marea Alta — Backend

FastAPI server with SQLite database for managing the party schedule, operating hours, and closed days. Includes a secure admin panel.

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
CSRF enforcement, the admin CRUD API, the server-rendered homepage, and
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

The admin panel is not linked from the public website. It is only accessible by navigating directly to `/admin`.

## API Endpoints

**Read endpoints are public** — the website fetches them with no login. Every
string comes back in **both languages**, so switching language needs no extra
request. The frontend picks the field matching the visitor's language and falls
back to English when a translation is blank.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/schedule` | Public | The whole week: titles, descriptions and hours per day |
| `GET` | `/api/closed-days` | Public | One-off date closures, both languages |
| `GET` | `/` | Public | The site, with the schedule rendered into the HTML |

**Write endpoints require an admin session and a CSRF token.**

| Method | Path | Description |
|---|---|---|
| `PUT` | `/api/schedule/{day}` | Save a day's titles, descriptions **and** hours together |
| `POST` | `/api/closed-days` | Add a closure (today or later) |
| `PATCH` | `/api/closed-days/{id}` | Correct a closure's wording later |
| `DELETE` | `/api/closed-days/{id}` | Remove a closure |

Reads send `Cache-Control: no-cache` so admin edits appear without visitors
having to hard-refresh.

Times are stored 24-hour (`HH:MM`) so the admin panel's `<input type="time">`
can populate them; the frontend formats them per locale.

## Server-Rendered Homepage

`/` and `/index.html` are **rendered**, not served off disk. `app/ssr.py` reads
`frontend/dist/index.html` and injects:

- the week's hours and party titles as plain HTML inside `<div id="app">`, so a
  crawler sees them without running any JavaScript, and
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

Anything else — hashed assets, the favicon — is still served by the static mount.
`Cache-Control: no-cache`, for the same reason the JSON reads use it. If
rendering fails for any reason the un-injected shell is served and the error is
logged, rather than the homepage going down.

`app/ssr.py` and `app/routers/api.py` share one set of loaders (`load_schedule`,
`load_closed_days`, `day_payload`), so the JSON and the HTML cannot describe
different weeks. `app/public_i18n.py` holds the handful of labels the rendered
block needs; the rest of the site's wording lives in `frontend/src/content/*.js`,
and a test in the frontend suite fails if the shared strings drift apart.

**nginx must proxy `/` here.** Serving `dist/index.html` straight off disk skips
the rendering and puts the schedule back out of reach of crawlers.

This is also where ticket #5's `openingHoursSpecification` and ticket #16's
multi-page routes belong.

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
