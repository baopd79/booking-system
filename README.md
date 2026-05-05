# Sports Court Booking System

[![CI](https://github.com/<your-username>/booking-system/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-username>/booking-system/actions/workflows/ci.yml)

Slot-based booking system với concurrency control, payment integration.

📄 **Design docs:** [README.md](./docs/README.md) (Phase 1) | [DESIGN.md](./docs/DESIGN.md) (Phase 2)
🤝 **Contributing:** [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## Quick start (≤ 5 phút)

### Yêu cầu

- Docker + Docker Compose
- [uv](https://docs.astral.sh/uv/) — package manager
- Python 3.12+ (chỉ cần nếu chạy local không qua Docker)

### 1. Clone + setup env

```bash
git clone <repo>
cd booking-system
cp .env.example .env

# Generate JWT secret (paste vào JWT_SECRET_KEY trong .env)
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 2. Install deps + git hooks

```bash
uv sync                # cài dep + tạo uv.lock
make hooks             # install pre-commit hooks
```

### 3. Start stack

```bash
make up
```

Stack gồm 3 service:
- `app` (FastAPI) — http://localhost:8000
- `db` (Postgres 16) — port 5432
- `redis` (Redis 7) — port 6379

### 4. Verify

```bash
curl http://localhost:8000/health
```

Output expected:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "env": "development",
  "checks": {"database": "up", "redis": "up"}
}
```

API docs: http://localhost:8000/docs

---

## Common commands

```bash
make up              # Start stack
make down            # Stop stack
make logs            # Tail app logs
make shell           # Bash vào container
make db-shell        # psql vào DB
make migrate         # Apply Alembic migrations
make migration m="add users"  # Tạo migration mới
make test            # Run pytest
make lint            # Ruff + mypy
make format          # Auto-format
make clean           # Xóa cache + volumes
```

---

## Project structure

```
app/
├── core/            # Config, DB, Redis, exceptions, security
├── modules/         # Bounded contexts (auth, facility, booking, payment, notification, report)
│   └── <name>/
│       ├── models.py       # SQLModel
│       ├── schemas.py      # Pydantic
│       ├── repository.py   # DB queries
│       ├── service.py      # Business logic
│       └── routes.py       # FastAPI router
├── jobs/            # Background jobs (cron)
└── main.py          # App entry point

alembic/             # Migrations
tests/               # unit / integration / concurrency
```

---

## SDLC

| Phase | Status |
|---|---|
| 1. CLARIFY | ✅ |
| 2. DESIGN | ✅ |
| 3. BUILD | ⏳ In progress |
| 4. HARDEN | — |
