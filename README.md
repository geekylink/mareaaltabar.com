# Marea Alta Surf Bar

The official website for Marea Alta Surf Bar in Montañita, Ecuador. Features live surf and tide conditions, plus the weekly party schedule.

## Project Structure

```
mareaaltabar.com/
├── frontend/          # Svelte 5 + Vite static site
├── backend/           # FastAPI + SQLite admin server
├── docs/              # Project documentation
└── README.md          # This file
```

## Quick Start

Two terminals. The backend owns the schedule data; the frontend displays it.

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
- Admin panel: <http://localhost:8000/admin> (not linked from the site)

### Production

```bash
cd frontend && npm run build     # emits frontend/dist
cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The backend serves `frontend/dist` from the same origin, so everything lives on
one domain and the site reads `/api/*` without CORS.

### Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Documentation

- [Frontend README](frontend/README.md) — content editing, schedule data flow, deployment
- [Backend README](backend/README.md) — API reference, admin panel, security, database schema

## Tech Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Frontend  | Svelte 5, Vite, vanilla CSS                     |
| Backend   | FastAPI, SQLAlchemy 2.0, SQLite, Pydantic       |
| Auth      | bcrypt password hashing, server-side sessions   |
| Deployment| Static host (frontend) + VPS/Cloud (backend)    |
