"""
In-memory cache (Redis o'rniga).
Keyinroq Redis ga o'tkazish mumkin.
"""

_waiting_orders: dict[str, set[str]] = {}


async def sadd(key: str, value: str) -> None:
    if key not in _waiting_orders:
        _waiting_orders[key] = set()
    _waiting_orders[key].add(value)


async def srem(key: str, value: str) -> None:
    if key in _waiting_orders:
        _waiting_orders[key].discard(value)


async def smembers(key: str) -> set[str]:
    return _waiting_orders.get(key, set())


class WaitingQueue:
    sadd = staticmethod(sadd)
    srem = staticmethod(srem)
    smembers = staticmethod(smembers)


waiting_queue = WaitingQueue()
