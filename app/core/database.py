"""
Async database engine + session factory.

Pattern: 1 engine global, mỗi request có 1 session riêng (qua dependency).

Lý do dùng async_sessionmaker thay vì AsyncSession trực tiếp:
- Factory pattern, dễ inject vào test (override)
- Quản lý lifecycle: tự rollback nếu exception, tự close
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ===== Engine =====
# pool_pre_ping: check connection còn sống trước khi dùng (tránh stale connection)
# echo: log SQL query — chỉ bật ở dev
engine: AsyncEngine = create_async_engine(
    str(settings.database_url),
    echo=settings.app_debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# ===== Session factory =====
# expire_on_commit=False: object vẫn dùng được sau commit (FastAPI hay cần)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yield session, auto rollback nếu exception, auto close.

    Usage:
        @router.get("/")
        async def handler(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
