# Production deployment runbook

This is the operations half of the deployment: the environment, the database
file, TLS, backups and the checks that tell you the site is alive. The
application-side recipe (build the frontend, run uvicorn) is in
[`../backend/README.md`](../backend/README.md).

The target shape is one small box:

```
Internet → nginx (TLS, gzip, static assets) → uvicorn (one worker) → SQLite file
```

The backend serves both the API and the rendered pages, so there is no CORS and
no second origin to configure.

## Environment file

Create `backend/.env` on the server. It is gitignored, as is `backend/data/`,
so neither secrets nor durable data are in version control.

```dotenv
ENVIRONMENT=production
DATABASE_PATH=/var/lib/marea-alta/marea_alta.db
COOKIE_SECURE=true
SESSION_TTL_HOURS=8
RATE_LIMIT_ATTEMPTS=5
RATE_LIMIT_WINDOW_MINUTES=10
LOG_RETENTION_DAYS=90
DAILY_LOG_PURGE=true
```

| Variable | Production value | Why |
|---|---|---|
| `ENVIRONMENT` | `production` | Disables `/docs` and `/openapi.json` |
| `DATABASE_PATH` | Absolute path outside the repo | Survives deploys and is easy to back up |
| `COOKIE_SECURE` | `true` | Session cookies are only sent over HTTPS |
| `SESSION_TTL_HOURS` | `8` | A shift-length session; lower it if the panel is shared |
| `RATE_LIMIT_ATTEMPTS` | `5` | Failed logins per IP before a block |
| `RATE_LIMIT_WINDOW_MINUTES` | `10` | Sliding window for that block |
| `LOG_RETENTION_DAYS` | `90` | How long login and change logs are kept |
| `DAILY_LOG_PURGE` | `true` | Let the app purge old logs itself |

There is **no `SECRET_KEY`**. Sessions are cryptographically random tokens stored
in the `sessions` table, not signed cookies, so there is no application secret
to generate, store or rotate. If an old `.env` still has one, delete the line —
nothing reads it.

Set the file to owner-only permissions:

```bash
chmod 600 backend/.env
```

The database directory should be writable by the service user and nobody else:

```bash
sudo install -d -o mareaalta -g mareaalta -m 750 /var/lib/marea-alta
```

Do not put the database under the repository. A `git clean`, a new checkout or a
container rebuild would then be able to delete the bar's data.

### Secrets hygiene

The only credentials this application holds are the admin password hashes in
the database. Keep it that way:

- `.env` is the only place for deployment-specific values. Never commit it.
- Never pass a password on a command line in production; use the hidden prompt
  in `manage_admin.py`, or the account page after the first login.
- A database backup contains password hashes. Treat the backup files with the
  same care as `.env`.
- Rotate an admin password from `/admin/account` (or `manage_admin.py password`)
  if it may have been shared. The account page also signs out the admin's other
  sessions, which is what you want after a suspected leak.

## Admin bootstrap

The first account must be created on the server, because there is no
self-service signup:

```bash
cd backend
source venv/bin/activate
python manage_admin.py create owner
```

The password is read from the terminal twice with hidden input. Use
`--password` only in development or automation: it is visible in shell history
and the process list.

After the first login, `manage_admin.py` is no longer required for day-to-day
work:

- `/admin/account` changes the signed-in admin's password.
- The same page creates a second admin, with the same password rules as the
  form (at least 8 characters, including a letter and a number).

`manage_admin.py list`, `delete` and `password` remain available as a
break-glass path if the panel cannot be reached.

## TLS and cookies

`COOKIE_SECURE=true` means the browser will not send the session cookie over
plain HTTP. That is only correct once HTTPS actually works, so bring up nginx
and Let's Encrypt first, then set the flag and restart the service.

nginx must:

- terminate TLS and redirect `http://` to `https://`;
- proxy **`/` and `/menu` to uvicorn**, not serve `dist/index.html` or
  `dist/menu.html` from disk. Serving the files directly bypasses server-side
  rendering and puts the hours and menu back out of reach of crawlers;
- serve `/assets/` from `frontend/dist/assets/` with a long cache lifetime;
- pass `Host`, `X-Forwarded-For` and `X-Forwarded-Proto` through, so audit-log
  IPs and any future redirect logic see the real client.

The session cookie is `HttpOnly`, `SameSite=Lax` and (with the flag above)
`Secure`. The CSRF cookie is readable by JavaScript on purpose; the API requires
its value in the `X-CSRF-Token` header and the HTML forms carry it in a hidden
field.

## Run one worker

Start uvicorn with no `--workers` flag:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

SQLite allows one writer at a time. The engine enables WAL and a 30-second busy
timeout, which lets readers continue while a writer commits and makes a second
writer wait rather than fail — but it does not turn SQLite into a multi-writer
database. At this traffic level one worker behind nginx is the correct and
lower-risk choice. See `backend/README.md` for the full explanation.

Bind to `127.0.0.1` and let nginx be the only public listener, so port 8000
cannot be reached around the TLS terminator.

## Health check and monitoring

Point an external monitor and the container healthcheck at:

```text
GET https://mareaaltabar.com/healthz
```

It returns `200 {"status":"ok"}` when the database answers and
`503 {"status":"unavailable"}` when it does not, always with
`Cache-Control: no-store`. Do not monitor `/` instead: the static page can
render perfectly while the API is down and the schedule is silently blank.

Run the same check locally after a deploy (or through nginx):

```bash
curl -fsS https://mareaaltabar.com/healthz
```

## Backups and restore

Back up the SQLite file, not the directory tree, and do it while the app is
running with SQLite's own backup command so a write cannot tear the copy:

```bash
sudo install -d -o mareaalta -g mareaalta -m 750 /var/backups/marea-alta
sudo -u mareaalta sqlite3 /var/lib/marea-alta/marea_alta.db \
  ".backup '/var/backups/marea-alta/marea_alta-$(date +%F).db'"
```

A nightly cron entry is enough:

```cron
15 4 * * * mareaalta sqlite3 /var/lib/marea-alta/marea_alta.db ".backup '/var/backups/marea-alta/marea_alta-$(date +\%F).db'"
```

Keep more than one day. A copy from yesterday does not help if the database was
already broken then; keep at least 14 daily files and one monthly file off the
box. `sqlite3 .backup` is safe while uvicorn is writing.

Restore drill — run this before you need it:

```bash
# Stop the app so nothing writes during the swap.
sudo systemctl stop marea-alta

sudo -u mareaalta cp /var/backups/marea-alta/marea_alta-2026-01-01.db \
  /var/lib/marea-alta/marea_alta.db
sudo -u mareaalta chmod 640 /var/lib/marea-alta/marea_alta.db

sudo systemctl start marea-alta
curl -fsS https://mareaaltabar.com/healthz
```

After restoring, check the site and the admin panel, and confirm the
`-wal`/`-shm` files are gone or regenerated rather than a stale pair being left
from the old database. Copying a database file while the service is running is
the one thing to avoid; `.backup` exists precisely to make that unnecessary.

## Deploy checklist

1. `cd frontend && npm test && npm run build`
2. `cd ../backend && python -m pytest tests/ -q`
3. Copy the code, keep `.env` and the database directory in place.
4. `sudo systemctl restart marea-alta`
5. `curl -fsS https://mareaaltabar.com/healthz`
6. Load `/`, `/menu` and `/admin/login`; confirm the rendered schedule/menu is
   present in the page source (not only after JavaScript runs).
7. Check `journalctl -u marea-alta` for a startup error you did not see in the
   HTTP check.

A rollback is a code checkout plus a restart; the database lives outside the
checkout, so a rollback does not lose content. If a release changed the schema,
restore the matching database backup before restarting the old code.
