import json
import logging
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_pool: Optional[aioredis.Redis] = None
_redis_available: bool = True


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis_pool, _redis_available
    if not _redis_available:
        return None
    if _redis_pool is None:
        try:
            _redis_pool = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )
            # Test the connection
            await _redis_pool.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable, running without cache: {e}")
            _redis_available = False
            _redis_pool = None
            return None
    return _redis_pool


async def cache_set(key: str, value: Any, ttl: int = 5) -> None:
    """Cache a value with TTL in seconds. Silently fails if Redis unavailable."""
    try:
        r = await get_redis()
        if r is None:
            return
        await r.setex(key, ttl, json.dumps(value))
    except Exception as e:
        logger.debug(f"Cache set failed for {key}: {e}")


async def cache_get(key: str) -> Optional[Any]:
    """Get cached value, returns None if missing/expired or Redis unavailable."""
    try:
        r = await get_redis()
        if r is None:
            return None
        data = await r.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.debug(f"Cache get failed for {key}: {e}")
    return None


async def cache_delete(key: str) -> None:
    try:
        r = await get_redis()
        if r is None:
            return
        await r.delete(key)
    except Exception as e:
        logger.debug(f"Cache delete failed for {key}: {e}")


async def publish_market_data(channel: str, data: dict) -> None:
    """Publish to Redis pub/sub for WebSocket broadcasting."""
    try:
        r = await get_redis()
        if r is None:
            return
        await r.publish(channel, json.dumps(data))
    except Exception as e:
        logger.debug(f"Redis publish failed: {e}")


async def close_redis():
    global _redis_pool, _redis_available
    if _redis_pool:
        try:
            await _redis_pool.close()
        except Exception:
            pass
        _redis_pool = None
    _redis_available = True  # Reset for next startup
