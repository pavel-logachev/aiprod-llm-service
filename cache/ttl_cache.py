import asyncio
import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class CacheEntry:
    value: str
    expires_at: float


class TTLCache:
    def __init__(
        self,
        ttl_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds должен быть положительным")
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= self._clock():
                self._entries.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: str) -> None:
        async with self._lock:
            self._entries[key] = CacheEntry(
                value=value,
                expires_at=self._clock() + self._ttl_seconds,
            )


def build_cache_key(
    *,
    message: str,
    model: str,
    temperature: float,
    system_prompt: str,
) -> str:
    canonical = json.dumps(
        {
            "message": message,
            "model": model,
            "temperature": temperature,
            "system_prompt": system_prompt,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

