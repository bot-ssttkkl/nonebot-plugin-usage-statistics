import asyncio
from typing import Generic, TypeVar, Type, Optional, Callable, Any

from nonebot import require

require("nonebot_plugin_datastore")

from nonebot_plugin_datastore import get_plugin_data

plugin_data = get_plugin_data("nonebot_plugin_usage_statistic")

T = TypeVar("T")


class PrefKey(Generic[T]):
    def __init__(self, key: str, pref_type: Type[T],
                 serializer: Optional[Callable[[T], Any]] = None,
                 deserializer: Optional[Callable[[Any], T]] = None):
        self._lock = None

        self.serializer = serializer
        if self.serializer is None:
            self.serializer = lambda x: x

        self.deserializer = deserializer
        if self.deserializer is None:
            self.deserializer = lambda x: x

        self.key = key
        self.pref_type = pref_type

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock


async def get_pref(key: PrefKey[T]) -> Optional[T]:
    data = await plugin_data.config.get(key.key)
    if data is None:
        return data
    else:
        return key.deserializer(data)


async def set_pref(key: PrefKey[T], value: T):
    if value is None:
        data = None
    else:
        data = key.serializer(value)
    await plugin_data.config.set(key.key, data)


async def inc_pref(key: PrefKey[int], *, with_lock: bool = True) -> int:
    async def handle():
        cur = await get_pref(key) or 0
        cur += 1
        await set_pref(key, cur)
        return cur

    if with_lock:
        async with key.lock:
            return await handle()
    else:
        return await handle()


__all__ = ("plugin_data",)
