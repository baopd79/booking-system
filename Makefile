.PHONY: help install hooks up down logs shell db-shell migrate migration seed-owner test lint format clean

help:
	@echo "Available commands:"
	@echo "  make install       - Sync deps với uv"
	@echo "  make hooks         - Install pre-commit hooks (lần đầu)"
	@echo "  make up            - Start docker-compose stack"
	@echo "  make down          - Stop stack"
	@echo "  make logs          - Tail app logs"
	@echo "  make shell         - Bash vào container app"
	@echo "  make db-shell      - psql vào DB"
	@echo "  make migrate       - Apply migrations"
	@echo "  make migration m=  - Create migration: make migration m='add users'"
	@echo "  make seed-owner    - Seed/update owner account"
	@echo "  make test          - Run pytest"
	@echo "  make lint          - Ruff check + mypy"
	@echo "  make format        - Ruff format"
	@echo "  make clean         - Xóa cache, volumes"

install:
	uv sync

hooks:
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg
	@echo "✅ Pre-commit hooks installed"

up:
	docker compose up -d --build
	@echo "✅ Stack started. App: http://localhost:8000/docs"

down:
	docker compose down

start:
	docker compose start
	@echo "✅ Stack started. App: http://localhost:8000/docs"

stop:
	docker compose stop

fastapilocal:
	uv run uvicorn app.main:app --reload --env-file .env.local

logs:
	docker compose logs -f app

shell:
	docker compose exec app bash

db-shell:
	docker compose exec db psql -U booking -d booking_db

migrate:
	docker compose exec app alembic upgrade head

migration:
	@if [ -z "$(m)" ]; then echo "❌ Usage: make migration m='message'"; exit 1; fi
	docker compose exec app alembic revision --autogenerate -m "$(m)"

seed-owner:
	docker compose exec app python -m app.modules.auth.seed_owner

test:
	docker compose exec app pytest -v

lint:
	uv run ruff check app/
	uv run mypy app/ || true

format:
	uv run ruff format app/
	uv run ruff check --fix app/

clean:
	docker compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
