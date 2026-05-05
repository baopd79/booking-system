"""
Redis client — dùng cho:
- Cache (sau này)
- Retry queue cho notification
- Distributed lock cho reconciliation job
"""

import redis.asyncio as redis

from app.core.config import settings

redis_client: redis.Redis = redis.from_url(
    str(settings.redis_url),
    encoding="utf-8",
    decode_responses=True,
    health_check_interval=30,
)


async def get_redis() -> redis.Redis:
    """FastAPI dependency."""
    return redis_client


async def check_redis_health() -> bool:
    """Health check — gọi từ /health endpoint."""
    try:
        await redis_client.ping()
        return True
    except Exception:
        return False
