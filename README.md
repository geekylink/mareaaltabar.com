# Marea Alta Surf Bar

The official website for Marea Alta Surf Bar in Montañita, Ecuador. Features live surf and tide conditions, the weekly party schedule, and the drinks menu.

## Project Structure

```
mareaaltabar.com/
├── frontend/          # Svelte 5 + Vite static site
├── backend/           # FastAPI + SQLite admin server
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
python manage_admin.py create admin yourpassword   # create the first admin
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
- Admin panel: <http://localhost:8000/admin> (not linked from the site)
- Admin logs: <http://localhost:8000/admin/logs> (read-only: logins, menu and schedule changes)

### Production

```bash
cd frontend && npm run build     # emits frontend/dist (index.html + menu.html)
cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The backend serves `frontend/dist` from the same origin, so everything lives on
one domain and the site reads `/api/*` without CORS.

`/` and `/menu` are **rendered**, not served straight off disk: the weekly
schedule, opening hours, closure notices and the drinks menu are injected into
the HTML so search engines can read them without running JavaScript. Proxy `/`
and `/menu` to the backend rather than serving the files directly from nginx,
or that rendering is skipped.

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
docker-compose exec web python manage_admin.py create admin 'yourpassword'
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
# Backend: auth, CRUD, migrations, admin-edit propagation, closed-day and menu filtering, logs
cd backend
python -m pytest tests/ -v

# Frontend: language switching, fallback, time formatting, closed-day handling, the menu
cd ../frontend
npm test
```

## Documentation

- [Frontend README](frontend/README.md) — content editing, schedule data flow, deployment
- [Backend README](backend/README.md) — API reference, admin panel, security, database schema

## Tech Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Frontend  | Svelte 5, Vite (two documents), vanilla CSS      |
| Backend   | FastAPI, SQLAlchemy 2.0, SQLite, Pydantic       |
| Auth      | bcrypt password hashing, server-side sessions   |
| Deployment| Static host (frontend) + VPS/Cloud (backend)    |
