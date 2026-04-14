"""Per-user rate limiter for incoming Telegram updates.

Sliding window in-memory counter; suitable for single-process polling.
For multi-instance or webhook fanout, move to Redis.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable, Deque

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """Drop messages beyond ``max_events`` per ``window_seconds`` per user.

    First overflow per window emits a one-time user-facing warning.
    """

    def __init__(self, max_events: int = 20, window_seconds: float = 60.0):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._buckets: dict[int, Deque[float]] = defaultdict(deque)
        self._warned: dict[int, float] = defaultdict(float)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        now = time.monotonic()
        bucket = self._buckets[user.id]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= self.max_events:
            last_warn = self._warned[user.id]
            if now - last_warn > self.window_seconds:
                self._warned[user.id] = now
                logger.warning("Rate-limited user %s (events=%d)", user.id, len(bucket))
                try:
                    if isinstance(event, Message):
                        await event.answer("⏳ Juda tez yuboryapsiz. Biroz kuting.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⏳ Sekinroq...", show_alert=False)
                except Exception:
                    pass
            return
        bucket.append(now)

        return await handler(event, data)
