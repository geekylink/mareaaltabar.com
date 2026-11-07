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
`/var/www/marea-alta` — adjust to match `DEPLOY_CHECKOUT`):

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

CI lives in `.github/workflows/ci.yml` and runs on every pull request and push
to `main`: the backend (`ruff` + `pytest`), the frontend (`svelte-check`,
Vitest, build and asset budget) and the deploy agent's own unit tests.

Deployment is **pull-based**: the VPS asks GitHub whether the current `main`
commit passed CI, then builds and restarts locally. GitHub never connects to the
server. That means:

- no inbound SSH port for deployments and no SSH private key in GitHub;
- no deploy secret on a GitHub runner that can write to the server;
- no self-hosted Actions runner on the VPS, which would let any workflow run
  arbitrary code there;
- the only outbound traffic is `git ls-remote`/`git fetch` and one GitHub API
  call per changed commit.

The agent is [`deploy/marea_deploy.py`](../deploy/marea_deploy.py), run by
`deploy/marea-deploy.service` from `deploy/marea-deploy.timer` every five
minutes. It refuses to deploy unless all of these are true:

1. the checkout is on `main`, has no local changes, and the remote commit is a
   fast-forward of it;
2. the latest Actions run for that exact commit, from a `push` event on `main`,
   is completed with `success`;
3. after fetching, `origin/main` still points at the same commit.

It then installs backend requirements, runs `npm ci && npm run build`, restarts
`marea-alta` through the one allowed sudo command, and polls
`http://127.0.0.1:8000/healthz`. Any failure resets the checkout to the previous
commit, rebuilds and restarts it, and exits non-zero so `systemctl status`
records the failed deploy.

The last successful SHA is kept in `.git/marea-deploy.state`. If the process is
killed between the fast-forward and the health check, the next run sees that the
checkout is ahead of the recorded deploy, rebuilds and restarts it, and still has
the previous SHA to roll back to. Both files can be moved with
`DEPLOY_STATE_FILE` and `DEPLOY_LOCK_FILE`; neither is tracked by Git.

### Install the agent

The VPS needs `git`, Python 3.12 with `venv`, Node 22 with `npm`, and `sudo`.
The agent creates `backend/venv` on its first run; if a venv already exists, it
must be writable by the service user because the agent updates it on every
deploy. Edit the unit if you use a user other than `mareaalta`.

Create the Linux user that owns the checkout and runs the service (the examples
use `mareaalta`). Clone the repository **as that user**:

```bash
sudo install -d -o mareaalta -g mareaalta /var/www/marea-alta
sudo -u mareaalta git clone git@github.com:geekylink/mareaaltabar.com.git \
  /var/www/marea-alta
```

For a public repository the clone may use HTTPS. For a private one, use a
read-only deploy key on the VPS (registered in the repository, not in Actions)
or a fine-grained token with `Contents: read`.

Install the script and the two units. The command in `/usr/local/bin` is a
symlink into the checkout, so the agent runs a newer copy of itself after it
deploys one:

```bash
sudo ln -sfn /var/www/marea-alta/deploy/marea_deploy.py /usr/local/bin/marea-deploy
sudo chmod 755 /var/www/marea-alta/deploy/marea_deploy.py
sudo install -m 644 deploy/marea-deploy.service /etc/systemd/system/
sudo install -m 644 deploy/marea-deploy.timer /etc/systemd/system/
sudo install -m 640 -o root -g mareaalta \
  deploy/marea-deploy.env.example /etc/marea-deploy.env
```

Edit `/etc/marea-deploy.env` and set `DEPLOY_REPO`, `DEPLOY_CHECKOUT` and
`DEPLOY_SERVICE`. The defaults for `DEPLOY_BRANCH`, `DEPLOY_WORKFLOW` and
`DEPLOY_HEALTH_URL` match this repository and the systemd examples.

The agent restarts the service through sudo and **only** that command:

```bash
command -v systemctl   # usually /usr/bin/systemctl
echo 'mareaalta ALL=(root) NOPASSWD: /usr/bin/systemctl restart marea-alta' \
  | sudo tee /etc/sudoers.d/marea-deploy
sudo chmod 440 /etc/sudoers.d/marea-deploy
sudo visudo -c
```

Enable the timer and run it once by hand:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now marea-deploy.timer
sudo systemctl start marea-deploy.service
journalctl -u marea-deploy.service -n 50 --no-pager
```

A manual start is also the recovery path after fixing a failed deploy. There is
no mode that skips the health check or the rollback.

### GitHub API quota

The repository is public, so the agent reads the Actions API anonymously. It
only calls the API when `git ls-remote` shows a commit it has not deployed yet,
and a five-minute timer stays far below the 60-request hourly anonymous limit.
If the repository becomes private, or the VPS shares an IP with other pollers,
create a fine-grained token with **Actions: read** only and set
`DEPLOY_GITHUB_TOKEN_FILE=/etc/marea-deploy/github-token`. Store that file
owned by the service user (or `root:mareaalta`) with mode `0600` (or `0640`),
readable only by the service user.

### What the agent will not do

- It will not deploy a pull-request run, a manual `workflow_dispatch`, or a run
  for a different commit.
- It will not rewrite a checkout with local changes or local commits. A failed
  fast-forward needs a human, which is deliberate: silently discarding a server
  edit is how a hotfix disappears.
- It never touches `backend/.env`, the database or the upload directory; they
  live outside the checkout.

If five minutes is too slow, lower `OnUnitActiveSec` in the timer. A webhook
receiver could start the same service immediately, but that adds an inbound
endpoint and a shared secret, so polling is the default.

## Deploy checklist

1. `cd frontend && npm run lint && npm test && npm run build && npm run budget`
2. `cd ../backend && python -m ruff check app tests && python -m pytest tests/ -q`
3. `cd .. && python -m unittest discover -s deploy/tests -v`
4. Push to `main` and confirm CI is green on that commit.
5. `sudo systemctl start marea-deploy.service` (or wait for the timer).
6. `journalctl -u marea-deploy.service -n 50 --no-pager` and confirm it
   deployed the commit CI passed.
7. `curl -fsS https://mareaaltabar.com/healthz`
8. `curl -fsS https://mareaaltabar.com/api/surf | head -c 200` and confirm it
   returns wave/tide fields, not a 502.
9. Load `/`, `/menu`, `/news` and `/admin/login`; confirm the rendered
   schedule/menu/posts are present in the page source (not only after JavaScript
   runs), and that the fonts load from `/fonts/` rather than Google.
10. Check `journalctl -u marea-alta` for a startup error you did not see in the
    HTTP check.

The agent rolls back automatically when the build, restart or health check
fails. To roll back by hand, `git reset --hard <previous>` in the checkout,
rebuild the frontend, restart `marea-alta` and run the health check. The
database lives outside the checkout, so a code rollback does not lose content.
If a release changed the schema, restore the matching database backup before
restarting the old code.
