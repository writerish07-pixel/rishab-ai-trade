import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings

_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _redis_pool


async def cache_set(key: str, value: Any, ttl: int = 5) -> None:
    """Cache a value with TTL in seconds."""
    r = await get_redis()
    await r.setex(key, ttl, json.dumps(value))


async def cache_get(key: str) -> Optional[Any]:
    """Get cached value, returns None if missing/expired."""
    r = await get_redis()
    data = await r.get(key)
    if data:
        return json.loads(data)
    return None


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)


async def publish_market_data(channel: str, data: dict) -> None:
    """Publish to Redis pub/sub for WebSocket broadcasting."""
    r = await get_redis()
    await r.publish(channel, json.dumps(data))


async def close_redis():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None
