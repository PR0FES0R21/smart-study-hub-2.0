# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project type and tooling
- Backend: FastAPI (Python)
- Data: MongoDB (motor), Redis (cache, pub/sub)
- Background jobs: Celery (Redis broker/backend)
- Realtime: WebSockets with a Redis bridge for multi-process broadcast
- Tests: pytest
- Lint/format/type-check: black, isort, flake8, mypy
- Containers: Docker, docker-compose (dev and prod)

Quick start
- Python 3.9+ recommended (CI runs 3.8–3.10; Docker uses 3.9)
- Copy environment file and install deps:
  - cp .env.example .env
  - python -m venv .venv && source .venv/bin/activate  # PowerShell: python -m venv .venv; . .venv/Scripts/Activate.ps1
  - python -m pip install -U pip
  - pip install -r requirements.txt

Common commands
- Run API (dev, auto-reload):
  - uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
- Run API (prod, as in Dockerfile):
  - gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
- Celery worker:
  - celery -A app.core.celery_app:celery_app worker --loglevel=info
- Docker Compose (development stack: app + MongoDB + Redis + tooling):
  - docker compose -f docker-compose.dev.yml up --build
- Docker Compose (production-like):
  - docker compose up --build -d
- Lint/format/type-check (check mode matches CI):
  - black --check app/
  - isort --check-only app/
  - flake8 app/
  - mypy app/ --ignore-missing-imports
- Apply formatting locally:
  - black app/
  - isort app/
- Run tests (pytest):
  - pytest -q
  - Run a single file: pytest tests/test_score_analytics.py -q
  - Run a single test: pytest tests/test_exam_analytics_unit.py::test_basic_flow -q
  - Filter by keyword: pytest -k "analytics and not slow" -q
- Health checks:
  - HTTP: curl http://localhost:8000/api/v1/system/health
  - WebSocket health: curl http://localhost:8000/health/websocket

Environment and configuration
- Source of truth: app/core/config.py (Pydantic BaseSettings)
- Load order: OS env vars, then .env (example in .env.example)
- Key variables (set them before running):
  - PROJECT_NAME
  - API_V1_STR (e.g., /api/v1)
  - DATABASE_URL, DATABASE_NAME (MongoDB)
  - REDIS_URL
  - SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
  - R2_* for object storage if used (see .env.example)
- Windows PowerShell example (temporary env for the session):
  - $env:DATABASE_URL = "mongodb://localhost:27017"
  - $env:DATABASE_NAME = "school_db_mvp"
  - $env:REDIS_URL = "redis://localhost:6379"
  - $env:SECRET_KEY = "replace-me"

High-level architecture and flow
- Entrypoint and app lifecycle
  - app/main.py defines the FastAPI app with a lifespan manager
  - Startup tasks run on boot (initialize_active_period_cache, create_default_admin)
  - WebSocket manager and Redis bridge are initialized during startup and closed during shutdown
  - CORS and onboarding middleware are applied globally

- API surface
  - app/api/v1/api.py composes all routers under the API_V1_STR prefix
  - Routes are grouped by domain: auth, users, subjects, classes, teaching_assignments, exams, exam_sessions, analytics (score/exam/teacher), profiles, periods, coordination, exports, etc.
  - Dependencies in app/api/v1/deps.py provide JWT-based auth (OAuth2PasswordBearer), role checks, active academic period resolution with cache, and typed DB access

- Data layer and cache
  - app/core/db.py creates a shared motor AsyncIOMotorClient bound to DATABASE_URL/DATABASE_NAME and a Redis client from REDIS_URL
  - CRUD modules under app/crud/ encapsulate MongoDB access and complex aggregation pipelines; use these instead of raw collection calls
  - Caching helpers (app/core/cache.*) are used to memoize common reads; invalidation is implemented alongside writes in the relevant CRUD paths

- Realtime (WebSockets)
  - app/core/websocket.py provides a ConnectionManager maintaining active connections, roles, rooms, and heartbeats; broadcasting supports role- and room-scoped messaging
  - app/core/redis_websocket.py bridges messages via Redis pub/sub so multiple app instances can broadcast consistently
  - WebSocket auth uses JWT via query param in deps.get_current_user_for_ws, with explicit close codes/reasons on failure

- Background processing
  - app/core/celery_app.py defines celery_app with Redis as broker/backend and imports task modules from app/tasks/*
  - Long-running operations (analytics calculations, Excel import/export, academic cycle transitions) run as Celery tasks

- Security and activity logging
  - Authentication: OAuth2 password flow at POST /api/v1/auth/login returns a JWT (token_type=bearer) signed with SECRET_KEY
  - Authorization is role-based in dependency wrappers (admin/teacher guards)
  - Activity logs are captured on login success/failure with request context and user metadata

- Notable domain model relationships
  - teaching_assignments is a central hub connecting teachers, classes, subjects, and academic periods; many permissions and analytics scopes derive from this link
  - The exam system typically flows: question_banks → question_sets → exams → exam_sessions → analytics

CI signals (what the pipeline runs so you can mirror locally)
- Test: pytest with coverage of app/, MongoDB and Redis services available
- Lint: black, isort, flake8, mypy on app/
- Security: bandit and safety reports
- Build: docker buildx, optional push on releases

Tips specific to this repo
- Prefer running MongoDB and Redis via docker-compose.dev for parity and convenience during local development
- Ensure DATABASE_URL/DATABASE_NAME/REDIS_URL are set in the environment; these are what app/core/config.py reads
- For production, align with the Dockerfile’s gunicorn invocation; use uvicorn with --reload only during development

Notes on existing docs/WARP.md (under docs/)
- Consider moving or consolidating content into this root WARP.md so agents can discover it automatically
- Update the Celery command to reference the celery_app instance explicitly:
  - celery -A app.core.celery_app:celery_app worker --loglevel=info
- Align the recommended production command with Dockerfile’s gunicorn-based entrypoint
- In the “Testing” section, prefer pytest invocations; for non-Python assets like tests/test_websocket.html or *.js load-tests, run them via a browser or node respectively instead of python
