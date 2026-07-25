# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build the React frontend into frontend/build
# ---------------------------------------------------------------------------
FROM node:20-slim AS frontend
WORKDIR /app/frontend

# Install deps first (cached unless the lockfile changes)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Build the SPA
COPY frontend/ ./
RUN npm run build          # -> /app/frontend/build

# ---------------------------------------------------------------------------
# Stage 2 — Python runtime: engine + FastAPI, serving the built SPA
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

# Install the Modulus engine + API extra (fastapi, uvicorn) from pyproject
COPY backend/ ./backend/
RUN pip install "./backend[api]"

# Copy the built SPA to where api.py serves it (../frontend/build from backend/)
COPY --from=frontend /app/frontend/build ./frontend/build

# api.py lives at the backend/ project root, next to pyproject.toml
WORKDIR /app/backend

# Render/Fly/Railway inject $PORT; default to 8000 for local runs
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
