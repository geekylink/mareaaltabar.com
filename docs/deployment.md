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
UPLOAD_DIR=/var/lib/marea-alta/uploads
COOKIE_SECURE=true
SESSION_TTL_HOURS=8
RATE_LIMIT_ATTEMPTS=5
RATE_LIMIT_WINDOW_MINUTES=10
LOG_RETENTION_DAYS=90
DAILY_LOG_PURGE=true
```

| Variable | Production value | Why |
|---|---|---|
| `ENVIRONMENT` | `production` | Disables `/docs` and `/openapi.json`, and turns on HSTS |
| `DATABASE_PATH` | Absolute path outside the repo | Survives deploys and is easy to back up |
| `UPLOAD_DIR` | Absolute path outside the repo | Uploaded images are files, not database rows; this directory needs its own backup |
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
sudo install -d -o mareaalta -g mareaalta -m 750 /var/lib/marea-alta/uploads
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

The PWA install prompt also requires HTTPS (localhost is the only exception), so
the app is not installable until TLS is live.

nginx must:

- terminate TLS and redirect `http://` to `https://`;
- proxy **`/`, `/menu` and `/news` to uvicorn**, not serve `dist/index.html`,
  `dist/menu.html` or `dist/news.html` from disk. Serving the files directly
  bypasses server-side rendering and puts the hours, menu and articles back out
  of reach of crawlers;
- proxy **`/uploads/` to uvicorn** as well. Those files are served by the app
  with their cache headers, and the upload directory is outside the web root;
- serve `/assets/` and `/fonts/` from `frontend/dist/` with a long cache
  lifetime. Asset names are hashed; the two font files have stable names and are
  replaced only with a service-worker version bump;
- serve `/sw.js` with `Cache-Control: no-cache` so a new service worker is
  picked up after a deploy. The worker itself caches the shell; do not add a
  long cache to it. `/manifest.json` and `/offline.html` can be served normally;
- pass `Host`, `X-Forwarded-For` and `X-Forwarded-Proto` through, so audit-log
  IPs and any future redirect logic see the real client.

The session cookie is `HttpOnly`, `SameSite=Lax` and (with the flag above)
`Secure`. The CSRF cookie is readable by JavaScript on purpose; the API requires
its value in the `X-CSRF-Token` header and the HTML forms carry it in a hidden
field.

## Compression and caching

uvicorn serves the app; nginx is responsible for squeezing the response. Add
this to the site's server block (paths assume the checkout is at
`/var/www/marea-alta` — adjust to match `DEPLOY_PATH`):

```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_comp_level 5;
gzip_types text/plain text/css text/javascript application/javascript
           application/json application/xml image/svg+xml;

# Hashed build output: safe to cache for a year, because a deploy changes the
# filename rather than the contents.
location /assets/ {
    alias /var/www/marea-alta/dist/assets/;
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;
}

# The two self-hosted variable fonts (#34). Names are stable, so bump the
# service worker version when either file changes.
location /fonts/ {
    alias /var/www/marea-alta/dist/fonts/;
    expires 1y;
    add_header Cache-Control "public, immutable";
    access_log off;
}

location = /sw.js {
    add_header Cache-Control "no-cache";
}
```

If `nginx -V` shows the brotli module, add `brotli on;` and a matching
`brotli_types` line; gzip stays as the fallback for clients that do not accept
brotli. Do not pre-compress the HTML rendered by FastAPI — it changes per request.

`GET /api/surf` already sets `Cache-Control: public, max-age=300` and the app
caches the Open-Meteo response in-process for fifteen minutes (#34), so a second
`proxy_cache` is optional. If you add one, keep it short and never put the admin
or write routes behind it.

The frontend has a build budget: `npm run budget` fails above 80 KB of gzipped
JavaScript, 16 KB of gzipped CSS or a 40 KB single chunk. CI runs it after
`npm run build`, so a dependency that doubles the bundle is caught before deploy.
Measure Lighthouse with Chrome DevTools mobile throttling after the first real
deploy; the app-side work (self-hosted preloaded fonts, one cached surf read and
lazy images) is done, but the nginx half only exists once this section is live.

## Security headers

FastAPI sets these on every response in `backend/app/main.py`; nginx should pass
them through rather than adding a second copy of any of them:

| Header | What it does |
|---|---|
| `Content-Security-Policy` | `default-src 'self'`; scripts only from this origin or with the response's nonce; fonts are self-hosted and the surf report is proxied, so no external origin is allowed |
| `Permissions-Policy` | Turns off camera, microphone, geolocation, payment and the other device APIs the site does not use |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` — the admin panel cannot be framed |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Strict-Transport-Security` | Production only: one year, `includeSubDomains` |

**HSTS is production-only for a reason.** Once a browser sees it, it refuses
plain HTTP for the host for a year, so serve it only after nginx terminates TLS
and redirects HTTP correctly. The app checks `ENVIRONMENT=production`. If any
subdomain is not HTTPS, drop `includeSubDomains` before enabling it.

**The CSP is nonce-based for scripts.** Each response gets a fresh
`secrets.token_urlsafe(16)` nonce, the header advertises it, and every inline
`<script>` carries the same value. In Jinja templates that is:

```html
<script nonce="{{ request.state.csp_nonce }}">
```

and in `app/ssr.py` the nonce is passed into `render_index` / `render_menu`.
`script-src` has no `'unsafe-inline'` and no `'unsafe-eval'`, so a script added
without the nonce will silently never run — check the browser console after
touching a template. `style-src` does allow `'unsafe-inline'` because the admin
templates use inline `style=` attributes, which cannot carry a nonce.

The FastAPI `/docs` page is exempt in development only: it loads Swagger UI from
a CDN and bootstraps it with an inline script. It is disabled in production.

Check the headers after a deploy:

```bash
curl -sI https://mareaaltabar.com/ \
  | grep -iE 'content-security-policy|strict-transport-security|permissions-policy'
```

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

The SQLite file is the bar's only copy of the schedule, hours, closures, menu,
content, submissions and reservations. [`scripts/backup.sh`](../scripts/backup.py)
copies it with SQLite's own backup API — not `cp`, which can capture a torn write
— verifies every copy with `PRAGMA integrity_check`, and prunes old files by date.

Uploaded images live in `UPLOAD_DIR`, not in the SQLite file. The database backup
does **not** contain them, so copy that directory off the box as well:

```bash
rsync -a --delete /var/lib/marea-alta/uploads/ backup@other-host:/srv/marea-alta/uploads/
```

```bash
sudo install -d -o mareaalta -g mareaalta -m 750 /var/backups/marea-alta

sudo -u mareaalta /opt/marea-alta/scripts/backup.sh \
  --database /var/lib/marea-alta/marea_alta.db \
  --backup-dir /var/backups/marea-alta \
  --retain-days 30 --retain-months 12
```

It writes two files per run:

```
marea_alta-2026-11-03.db   # daily, kept for --retain-days
marea_alta-2026-11.db      # monthly, kept for --retain-months
```

The daily file is overwritten on each run that day, so the last run wins. The
monthly file is refreshed too, so it always holds the latest backup of its month.
Both live on the same disk until you copy them off the box, which is the point —
a backup on the disk that failed is not a backup:

```bash
rsync -a --delete /var/backups/marea-alta/ backup@other-host:/srv/marea-alta/
```

A nightly cron entry is enough:

```cron
15 4 * * * mareaalta /opt/marea-alta/scripts/backup.sh --database /var/lib/marea-alta/marea_alta.db --backup-dir /var/backups/marea-alta >> /var/log/marea-backup.log 2>&1
```

Check that the most recent run is good at any time — this reads every backup in
the directory and fails loudly on a truncated or corrupt one:

```bash
scripts/backup.sh --database /var/lib/marea-alta/marea_alta.db \
  --backup-dir /var/backups/marea-alta --verify
```

Restore drill — run this before you need it, into a scratch directory, and
confirm the schedule comes back:

```bash
# 1. Restore the candidate into a scratch copy, not over the live file.
sudo -u mareaalta cp /var/backups/marea-alta/marea_alta-2026-11-03.db \
  /tmp/marea-restore-check.db
sudo -u mareaalta sqlite3 /tmp/marea-restore-check.db \
  "SELECT day, title_en FROM events ORDER BY day;"
```

If the rows look right, do the real swap with the app stopped so nothing writes
during it:

```bash
sudo systemctl stop marea-alta

sudo -u mareaalta cp /var/backups/marea-alta/marea_alta-2026-11-03.db \
  /var/lib/marea-alta/marea_alta.db
sudo -u mareaalta chmod 640 /var/lib/marea-alta/marea_alta.db

sudo systemctl start marea-alta
curl -fsS https://mareaaltabar.com/healthz
```

After restoring, check the site and the admin panel, and confirm the
`-wal`/`-shm` files are gone or regenerated rather than a stale pair being left
from the old database. Copying a database file while the service is running is
the one thing to avoid; the backup script exists precisely to make that
unnecessary.

## Automated deploy

`.github/workflows/ci.yml` runs the backend (`ruff`, `pytest`) and frontend
(`svelte-check`, Vitest, build) on every push and pull request.
`.github/workflows/deploy.yml` waits for that run to succeed on `main`, then:

1. builds `frontend/dist` on the runner;
2. rsyncs `backend/` (excluding `venv`, `.env`, `data` and `__pycache__`) and
   `frontend/dist/` to the checkout on the server;
3. installs Python dependencies with the server's own `venv`;
4. runs `sudo systemctl restart marea-alta`.

It is skipped until you set the repository variable `DEPLOY_ENABLED=true` and
the secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`,
`DEPLOY_KNOWN_HOSTS` and `DEPLOY_PATH`. The service user needs passwordless
sudo for exactly `systemctl restart marea-alta`. The deploy never touches the
server's `.env`, database or upload directory.

Manual deploys remain possible; use the checklist below.

## Deploy checklist

1. `cd frontend && npm run lint && npm test && npm run build && npm run budget`
2. `cd ../backend && python -m ruff check app tests && python -m pytest tests/ -q`
3. Copy the code, keep `.env` and the database directory in place.
4. `sudo systemctl restart marea-alta`
5. `curl -fsS https://mareaaltabar.com/healthz`
6. `curl -fsS https://mareaaltabar.com/api/surf | head -c 200` and confirm it
   returns wave/tide fields, not a 502.
7. Load `/`, `/menu`, `/news` and `/admin/login`; confirm the rendered
   schedule/menu/posts are present in the page source (not only after JavaScript
   runs), and that the fonts load from `/fonts/` rather than Google.
8. Check `journalctl -u marea-alta` for a startup error you did not see in the
   HTTP check.

A rollback is a code checkout plus a restart; the database lives outside the
checkout, so a rollback does not lose content. If a release changed the schema,
restore the matching database backup before restarting the old code.
