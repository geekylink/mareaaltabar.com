# syntax=docker/dockerfile:1
#
# Single-image build for the whole Marea Alta site: the FastAPI backend serves
# both the JSON API and the built Svelte frontend from one origin on one port.
#
# Layout matters. `backend/app/ssr.py` resolves the frontend as
# `BACKEND_DIR.parent / "frontend" / "dist"` (and `main.py` mounts that path), so
# the image keeps the repo's shape: /app/backend and /app/frontend/dist. Do not
# flatten them.

# --- Stage 1: build the frontend (Svelte 5 + Vite) --------------------------
FROM node:20-alpine AS frontend

WORKDIR /build

# Dependency layer first, so a source edit does not re-run `npm ci`.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# Emits /build/dist/{index.html,menu.html,assets/}
RUN npm run build


# --- Stage 2: runtime (FastAPI + built frontend) ----------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

# Runtime dependencies only: everything above the "# Test suite" marker in
# requirements.txt. Keeps pytest/httpx out of the production image while leaving
# requirements.txt as the single source of truth.
COPY backend/requirements.txt ./
RUN sed '/^# Test suite/,$d' requirements.txt > requirements.runtime.txt \
 && pip install -r requirements.runtime.txt \
 && rm requirements.runtime.txt

# Backend source
COPY backend/ ./

# Built frontend, at the exact path app/ssr.py and app/main.py expect.
COPY --from=frontend /build/dist /app/frontend/dist

# Unprivileged runtime user; /data is the persistence mount.
RUN useradd --create-home --uid 10001 appuser \
 && mkdir -p /data \
 && chown -R appuser:appuser /app /data
USER appuser

# The app's database (and therefore sessions and logs) lives on the volume.
ENV DATABASE_PATH=/data/marea_alta.db
VOLUME ["/data"]

EXPOSE 8000

# Health endpoint: 200 once the app is serving and the database answers. The
# endpoint is public and uncached, so it is safe for a monitor to poll.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')" || exit 1

# One worker on purpose: SQLite does not tolerate concurrent writers, and this
# is a single small site. Do not add --workers N.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
