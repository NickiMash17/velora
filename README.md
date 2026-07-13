# Velora

The Digital Workforce Platform. See [`AGENTS.md`](./AGENTS.md) for the engineering charter and [`docs/`](./docs/README.md) for product and architecture documentation — read those before making changes.

**Status:** Sprint 1, Milestone 1 (Platform Foundation) complete. No business logic exists yet — see [`docs/architecture/README.md`](./docs/architecture/README.md) for what's designed but not yet built.

## Prerequisites

- Python 3.13+ and a way to create a virtualenv
- Node.js 20+ and npm
- Docker Desktop (for local Postgres/Redis)

## Local Setup

### 1. Start Postgres and Redis

```bash
docker compose up -d
```

This starts Postgres on host port **5433** (not 5432 — see the note in `docker-compose.yml` if you're wondering why) and Redis on 6379.

### 2. Backend

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env            # adjust if your local ports differ
alembic upgrade head            # currently a no-op — no models exist yet
uvicorn app.main:app --reload
```

Verify: `curl http://localhost:8000/healthz` and `curl http://localhost:8000/readyz`.

Run tests: `pytest` (unit tests only need Python; `tests/integration/` additionally requires Docker, since it spins up ephemeral Postgres/Redis containers via testcontainers rather than relying on the compose stack above).

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` — you'll see a Milestone 1 foundation-verification page, not the product landing page (that's a later milestone; see `docs/product/WireframeSpec.md §3`).

## Repository Layout

```
backend/    FastAPI modular monolith — see docs/engineering/EngineeringStandards.md §2.1
frontend/   Next.js 15 (App Router) — see docs/engineering/EngineeringStandards.md §2.2
docs/       Product and architecture documentation — the source of truth
AGENTS.md   Engineering charter — read this first
```
