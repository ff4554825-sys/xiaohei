from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
import hashlib

from ..types import Event, EventType


class ResponseStore:
    def __init__(self, ttl_hours: int = 24, event_bus=None):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._event_bus = event_bus
        logger.info("ResponseStore initialized")

    def _get_key(self, prompt: str, model: str = "default") -> str:
        return hashlib.md5(f"{model}:{prompt}".encode()).hexdigest()

    def get(self, prompt: str, model: str = "default") -> Optional[Any]:
        key = self._get_key(prompt, model)
        entry = self._cache.get(key)

        if entry:
            if datetime.now() < entry["expires_at"]:
                entry["access_count"] += 1
                logger.debug(f"Cache hit for prompt: {key[:8]}")
                return entry["response"]
            else:
                del self._cache[key]
                logger.debug(f"Cache expired for prompt: {key[:8]}")

        logger.debug(f"Cache miss for prompt: {key[:8]}")
        return None

    def set(self, prompt: str, response: Any, model: str = "default") -> None:
        key = self._get_key(prompt, model)
        self._cache[key] = {
            "response": response,
            "expires_at": datetime.now() + self._ttl,
            "created_at": datetime.now(),
            "access_count": 1,
        }

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": "Response cached",
                        "key": key[:8],
                    },
                    source="response_store",
                )
            )

        logger.debug(f"Cache set for prompt: {key[:8]}")

    def exists(self, prompt: str, model: str = "default") -> bool:
        key = self._get_key(prompt, model)
        entry = self._cache.get(key)

        if entry and datetime.now() < entry["expires_at"]:
            return True
        return False

    def invalidate(self, prompt: str, model: str = "default") -> bool:
        key = self._get_key(prompt, model)

        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated for prompt: {key[:8]}")
            return True
        return False

    def cleanup(self) -> int:
        now = datetime.now()
        expired_keys = [k for k, v in self._cache.items() if now >= v["expires_at"]]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._cache)
        access_count = sum(v["access_count"] for v in self._cache.values())
        avg_access = access_count / total if total > 0 else 0

        return {
            "total_entries": total,
            "total_accesses": access_count,
            "average_accesses": round(avg_access, 2),
        }
