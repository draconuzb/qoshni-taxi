"""Session token store and login rate limiter.

Uses Redis when ``REDIS_URL`` is configured; falls back to in-memory storage
for development. The in-memory fallback is NOT safe for multi-process /
multi-instance deployments.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from infrastructure.config import settings

logger = logging.getLogger(__name__)

_redis = None
if settings.redis_url:
    try:
        import redis.asyncio as redis_async
        _redis = redis_async.from_url(settings.redis_url, decode_responses=True)
        logger.info("Session store: Redis enabled (%s)", settings.redis_url)
    except Exception as e:
        logger.warning("Redis init failed, falling back to memory: %s", e)
        _redis = None
else:
    logger.warning("REDIS_URL not set — using in-memory session store (dev only)")


_SESSION_PREFIX = "session:"
_RL_PREFIX = "ratelimit:login:"

_mem_sessions: dict[str, float] = {}
_mem_ratelimit: dict[str, list[float]] = {}


async def session_create(token: str, ttl_seconds: int) -> None:
    if _redis is not None:
        await _redis.setex(_SESSION_PREFIX + token, ttl_seconds, "1")
    else:
        _mem_sessions[token] = time.time() + ttl_seconds


async def session_is_valid(token: str) -> bool:
    if not token:
        return False
    if _redis is not None:
        try:
            return bool(await _redis.exists(_SESSION_PREFIX + token))
        except Exception as e:
            logger.error("Redis session check failed: %s", e)
            return False
    expires = _mem_sessions.get(token)
    if expires is None:
        return False
    if expires < time.time():
        _mem_sessions.pop(token, None)
        return False
    return True


async def session_delete(token: str) -> None:
    if not token:
        return
    if _redis is not None:
        try:
            await _redis.delete(_SESSION_PREFIX + token)
        except Exception as e:
            logger.error("Redis session delete failed: %s", e)
    _mem_sessions.pop(token, None)


async def rate_limit_check(key: str, max_attempts: int, window_seconds: int) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds). Logs one attempt when allowed."""
    now = time.time()
    if _redis is not None:
        try:
            redis_key = _RL_PREFIX + key
            count = await _redis.incr(redis_key)
            if count == 1:
                await _redis.expire(redis_key, window_seconds)
            if count > max_attempts:
                ttl = await _redis.ttl(redis_key)
                return False, max(ttl, 1)
            return True, 0
        except Exception as e:
            logger.error("Redis rate-limit failed, allowing: %s", e)
            return True, 0
    bucket = _mem_ratelimit.setdefault(key, [])
    bucket[:] = [t for t in bucket if t > now - window_seconds]
    if len(bucket) >= max_attempts:
        return False, int(window_seconds - (now - bucket[0])) + 1
    bucket.append(now)
    return True, 0


async def close() -> None:
    if _redis is not None:
        try:
            await _redis.close()
        except Exception:
            pass
