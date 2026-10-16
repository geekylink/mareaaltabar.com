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

### Tests

```bash
# Backend: auth, CRUD, migrations, admin-edit propagation, closed-day and menu filtering
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
