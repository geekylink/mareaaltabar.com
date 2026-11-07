# Marea Alta Surf Bar

The official website for Marea Alta Surf Bar in Montañita, Ecuador. Features live surf and tide conditions, the weekly party schedule, the drinks menu and a news page.

## Project Structure

```
mareaaltabar.com/
├── frontend/          # Svelte 5 + Vite static site
├── backend/           # FastAPI + SQLite admin server
├── deploy/            # Pull-based deploy agent and systemd units
├── docs/              # Project documentation
└── README.md          # This file
```

## Quick Start

Two terminals. The backend owns the schedule and menu data; the frontend displays it.

```bash
# Terminal 1 — backend on :8000
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage_admin.py create admin                # create the first admin (prompts for a password)
uvicorn app.main:app --reload --port 8000
```

```bash
# Terminal 2 — frontend on :5173 (proxies /api and /admin to :8000)
cd frontend
npm install
npm run dev
```

- Site: <http://localhost:5173>
- Drinks menu: <http://localhost:5173/menu> (or `/menu` on the backend port)
- News: <http://localhost:5173/news> (or `/news` on the backend port)
- Admin panel: <http://localhost:8000/admin> (not linked from the site)
- Admin logs: <http://localhost:8000/admin/logs> (read-only: logins, menu and schedule changes)

### Production

```bash
cd frontend && npm run build     # emits frontend/dist (index.html, menu.html, news.html)
cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The backend serves `frontend/dist` from the same origin, so everything lives on
one domain and the site reads `/api/*` without CORS.

`/` and `/menu` are **rendered**, not served straight off disk: the weekly
schedule, opening hours, closure notices and the drinks menu are injected into
the HTML so search engines can read them without running JavaScript. `/news` and
`/news/<slug>` work the same way, with each article's title, description,
canonical URL and `BlogPosting` data rendered per post. Proxy `/`, `/menu` and
`/news` to the backend rather than serving the files directly from nginx, or that
rendering is skipped.

### Continuous integration and deploy

`.github/workflows/ci.yml` runs on every pull request and push to `main`:
`ruff` and `pytest` for the backend, `svelte-check`, Vitest, a production build
and the asset budget for the frontend, and the deploy agent's unit tests.

Deployment is pull-based. `deploy/marea-deploy.timer` runs
`deploy/marea_deploy.py` on the VPS every five minutes; it deploys the current
`main` only after the GitHub Actions run for that exact commit has completed
successfully. GitHub never connects to the server, so there is no SSH deploy key
in Actions and no host secret in the repository. See
[the deployment runbook](docs/deployment.md#automated-deploy) for installation,
the one allowed sudo command and rollback behaviour.

### Docker (single container)

One container runs the whole site: the Dockerfile builds the frontend and copies
it into the image beside the backend, and FastAPI serves the API, `/`, `/menu`
and the assets from a single origin and a single port.

```bash
cp .env.example .env          # optional: set APP_PORT (default 8080)
docker-compose up -d --build  # build and start; site on http://localhost:8080
docker-compose logs -f web    # follow logs
docker-compose down           # stop (data is kept)
```

- **One port.** `8080` on the host by default (`APP_PORT` in `.env`), `8000`
  inside the container. That is the only port opened.
- **Data persists.** The SQLite database — which also holds admin sessions and
  the login/change logs — lives in the named volume `marea_alta_data` at
  `/data`. It survives rebuilds, `docker-compose down` and upgrades. Wipe it
  deliberately with `docker-compose down -v`.
- **One worker.** SQLite does not tolerate concurrent writers, and the app runs
  a single uvicorn worker on purpose.

Create the first admin inside the running container (it writes to the volume):

```bash
docker-compose exec web python manage_admin.py create admin   # prompts for a password
```

**TLS.** This setup has no TLS of its own, so `COOKIE_SECURE` is `false` in
`docker-compose.yml` — otherwise the browsers would drop the session cookie over
plain HTTP and admin login would fail. Once HTTPS terminates in front of the
container (Cloudflare, or nginx on the host), set `COOKIE_SECURE: "true"`.

#### Verifying a build

`tests/docker_smoke_test.sh` builds the image, starts it on an isolated project
and port, and checks the site end to end — the rendered pages, the API, the
single published port, the volume, admin login and persistence across a restart.
See [tests/README.md](tests/README.md).

### Tests

```bash
# Everything at once: frontend, backend and the docker smoke test, with a summary
tests/test_all.sh            # --silent prints only failures and the summary

# Backend: auth, CRUD, migrations, admin-edit propagation, closed-day and menu filtering, logs, news
cd backend
python -m pytest tests/ -v
python -m pytest tests/ --cov=app --cov-branch --cov-fail-under=90   # coverage gate used by CI
python -m ruff check app tests

# Frontend: language switching, fallback, time formatting, closed-day handling, the menu, news
cd ../frontend
npm run lint
npm test
npm run test:coverage        # coverage gate used by CI

# Browser tests: Chromium against a throwaway SQLite database on port 8010.
# `test:e2e` builds the frontend first and never touches backend/data/ or .env.
npx playwright install chromium   # first run only
npm run test:e2e

# Deploy agent: CI gate, fast-forward and clean-tree checks, rollback
cd ..
python3 -m unittest discover -s deploy/tests -v
```

The Playwright suite needs the backend's Python dependencies in the same
interpreter. If they live in a virtualenv, pass it through `PYTHON`:

```bash
cd frontend
PYTHON=../backend/.venv/bin/python npm run test:e2e
```

`tests/test_all.sh` keeps the terminal short and writes the full output of every
suite to `tests/test_all.log`, replaced on each run.

## Documentation

- [Still needed](STILL_NEEDED.md) — what is not done and what only the owner can do: deploy, credentials, real content, unrun checks
- [Frontend README](frontend/README.md) — content editing, schedule data flow, deployment
- [Backend README](backend/README.md) — API reference, admin panel, security, database schema

## Tech Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Frontend  | Svelte 5, Vite (two documents), vanilla CSS      |
| Backend   | FastAPI, SQLAlchemy 2.0, SQLite, Pydantic       |
| Auth      | bcrypt password hashing, server-side sessions   |
| Deployment| Static host (frontend) + VPS/Cloud (backend)    |
