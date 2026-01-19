"""Redis initialization and client management."""

from redis import asyncio as aioredis

from app.core.config import get_settings
from app.core.logger import logger

redis_client: aioredis.Redis | None = None


async def init_redis() -> aioredis.Redis:
    """Initialize Redis client."""
    global redis_client
    # Use get_settings() to always get current settings (important for env switching)
    settings = get_settings()
    redis_client = await aioredis.from_url(
        settings.redis.url,
        encoding="utf-8",
        decode_responses=True,
        password=settings.redis.password,
        max_connections=50
    )
    # 验证连接是否成功
    pong = await redis_client.ping()
    if pong:
        logger.info(f"Redis connection established successfully (URL: {settings.redis.url})")
    else:
        logger.error("Redis connection failed: ping returned False")
        raise RuntimeError("Failed to establish Redis connection")
    return redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        logger.info("Redis client closed")
        redis_client = None


def get_redis() -> aioredis.Redis:
    """Get Redis client instance."""
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_client
