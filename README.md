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

### Frontend (Development)

```bash
cd frontend
npm install
npm run dev
```

The site will be available at `http://localhost:5173`.

### Backend (Development)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create an admin user
python manage_admin.py create admin yourpassword

# Start the server
uvicorn app.main:app --reload --port 8000
```

The admin panel will be available at `http://localhost:8000/admin`.

## Documentation

- [Frontend README](frontend/README.md) — Svelte site structure, content editing, deployment
- [Backend README](backend/README.md) — API docs, admin panel, security, database schema

## Tech Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Frontend  | Svelte 5, Vite, vanilla CSS                     |
| Backend   | FastAPI, SQLAlchemy 2.0, SQLite, Pydantic       |
| Auth      | bcrypt password hashing, server-side sessions   |
| Deployment| Static host (frontend) + VPS/Cloud (backend)    |
