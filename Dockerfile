# ===== Stage 1: builder =====
FROM python:3.12-slim AS builder

# Install uv (single binary, không cần pip)
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /uvx /bin/

WORKDIR /app

# Copy dependency files trước (tận dụng Docker cache layer)
COPY pyproject.toml uv.lock* ./

# Cài dep vào /app/.venv
# --frozen: dùng đúng lock, fail nếu lock không khớp
# --no-install-project: chỉ cài dep, không cài project (chưa có code)
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --frozen --no-install-project --no-dev

# ===== Stage 2: runtime =====
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy venv từ builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
