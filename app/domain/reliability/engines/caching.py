import json
import logging
from typing import Any, Optional, Callable
from functools import wraps

from app.core.config import settings
import redis.asyncio as redis

logger = logging.getLogger("hunteros.reliability")

# Global Redis Pool
redis_pool = None

def get_redis() -> redis.Redis:
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_pool

class CacheEngine:
    """
    Intelligent caching for frequently used business contexts, dashboards, and AI contexts.
    Supports automatic TTL and invalidation.
    """

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        client = get_redis()
        try:
            val = await client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
        return None

    @staticmethod
    async def set(key: str, value: Any, ttl_seconds: int = 300):
        client = get_redis()
        try:
            await client.set(key, json.dumps(value), ex=ttl_seconds)
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")

    @staticmethod
    async def invalidate(key: str):
        client = get_redis()
        try:
            await client.delete(key)
        except Exception as e:
            logger.warning(f"Cache invalidate failed for {key}: {e}")


def cached(key_prefix: str, ttl: int = 300):
    """
    Decorator to cache the result of an async function.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Construct a unique key
            # (In production, you'd serialize args/kwargs properly)
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            
            cached_val = await CacheEngine.get(cache_key)
            if cached_val is not None:
                return cached_val
                
            result = await func(*args, **kwargs)
            await CacheEngine.set(cache_key, result, ttl_seconds=ttl)
            return result
        return wrapper
    return decorator
