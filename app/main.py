"""
FastAPI app entry point.

Bootstrap order:
1. Load config (settings)
2. Create app + register exception handlers
3. Register routers (modules) — Phase 3 sẽ thêm dần
4. Lifespan: startup/shutdown hook
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import AppError
from app.core.redis import check_redis_health, redis_client
from app.modules.auth.routes import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup + shutdown hook.
    - Startup: kiểm tra connection (fail-fast nếu DB/Redis down)
    - Shutdown: đóng connection pool
    """
    # Startup
    print(f"🚀 Starting app in {settings.app_env} mode")
    yield
    # Shutdown
    print("👋 Shutting down")
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(
    title="Sports Court Booking System",
    description="Slot-based booking with concurrency control",
    version="0.1.0",
    debug=settings.app_debug,
    lifespan=lifespan,
)

# ===== CORS =====
# MVP: allow all (dev). Production cần config domain cụ thể.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Exception handler =====
# Convert domain error → HTTP response theo format error chuẩn (DESIGN.md 4.1)
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


# ===== Health check =====
@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check — verify app + DB + Redis đang chạy.
    Trả 200 nếu tất cả OK, 503 nếu có dep down.
    """
    redis_ok = await check_redis_health()

    # DB health: thử query đơn giản
    db_ok = False
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    all_ok = redis_ok and db_ok
    status = 200 if all_ok else 503

    return JSONResponse(
        status_code=status,
        content={
            "status": "healthy" if all_ok else "unhealthy",
            "version": "0.1.0",
            "env": settings.app_env,
            "checks": {
                "database": "up" if db_ok else "down",
                "redis": "up" if redis_ok else "down",
            },
        },
    )


@app.get("/", tags=["system"])
async def root():
    return {"message": "Booking System API", "docs": "/docs"}


# ===== Module routers =====
app.include_router(auth_router)
