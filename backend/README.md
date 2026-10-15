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
CSRF enforcement, the admin CRUD API, and end-to-end propagation of admin edits
to the public read endpoints. Tests never touch `data/marea_alta.db`.

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

- **Party Schedule** (`/admin/schedule`): Edit titles, descriptions, and times for each weekday
- **Operating Hours**: Set open/close times and mark days as closed
- **Closed Days**: Add specific date closures (holidays, private events, etc.)

The admin panel is not linked from the public website. It is only accessible by navigating directly to `/admin`.

## API Endpoints

**Read endpoints are public** — the website fetches them with no login. They are
the single source of truth for the party schedule.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/events` | Public | List all 7 day events |
| `GET` | `/api/hours` | Public | List all 7 day hours |
| `GET` | `/api/closed-days` | Public | List all closed days |

**Write endpoints require an admin session and a CSRF token.**

| Method | Path | Description |
|---|---|---|
| `PUT` | `/api/events/{day}` | Update event for a weekday (0=Sun, 6=Sat) |
| `PUT` | `/api/hours/{day}` | Update hours for a weekday |
| `POST` | `/api/closed-days` | Add a closed day (today or later) |
| `DELETE` | `/api/closed-days/{id}` | Remove a closed day |

Reads send `Cache-Control: no-cache` so admin edits appear without visitors
having to hard-refresh.

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
| `time` | TEXT | Display time string |
| `title` | TEXT | Event name |
| `note` | TEXT | Description |
| `created_at` | DATETIME | Auto-set |
| `updated_at` | DATETIME | Auto-set |

### `hours`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `day` | INTEGER UNIQUE | 0=Sun ... 6=Sat |
| `open_time` | TEXT | e.g. "16:00" |
| `close_time` | TEXT | e.g. "04:00" |
| `is_closed` | BOOLEAN | 0 or 1 |
| `created_at` | DATETIME | Auto-set |
| `updated_at` | DATETIME | Auto-set |

### `closed_days`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `date` | TEXT UNIQUE | YYYY-MM-DD format |
| `reason` | TEXT | Optional reason |
| `created_at` | DATETIME | Auto-set |
| `updated_at` | DATETIME | Auto-set |
