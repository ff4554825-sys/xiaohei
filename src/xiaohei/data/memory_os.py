from typing import List, Dict, List, Any, Optional
from uuid import UUID
from loguru import logger
from datetime import datetime, timedelta
import asyncio

from ..types import MemoryLevel, MemoryItem


class MemoryOS:
    def __init__(self, memory_store=None):
        self._memory_store = memory_store
        self._scratchpad: Dict[str, Any] = {}
        self._working: Dict[str, Any] = {}
        self._consolidation_interval = 300
        self._consolidation_task = None
        logger.info("MemoryOS initialized")

    async def start(self):
        if self._consolidation_task is None:
            self._consolidation_task = asyncio.create_task(self._run_consolidation())
            logger.info("MemoryOS consolidation task started")

    async def stop(self):
        if self._consolidation_task:
            self._consolidation_task.cancel()
            self._consolidation_task = None
            logger.info("MemoryOS consolidation task stopped")

    async def _run_consolidation(self):
        while True:
            await asyncio.sleep(self._consolidation_interval)
            await self._consolidate_memory()

    async def _consolidate_memory(self):
        logger.debug("Starting memory consolidation")

        scratchpad_keys = list(self._scratchpad.keys())
        for key in scratchpad_keys:
            item = self._scratchpad.pop(key)
            self._working[key] = item

        working_items = list(self._working.items())
        if len(working_items) > 100:
            working_items.sort(key=lambda x: x[1].get("accessed_at", datetime.min), reverse=True)
            items_to_persist = working_items[:50]
            items_to_keep = working_items[50:]

            for key, item in items_to_persist:
                if self._memory_store:
                    await self._memory_store.write(
                        MemoryItem(
                            level=MemoryLevel.EPISODIC,
                            key=key,
                            value=item.get("value"),
                            created_at=item.get("created_at", datetime.now()),
                            accessed_at=item.get("accessed_at", datetime.now()),
                        )
                    )
                del self._working[key]

            self._working = dict(items_to_keep)

        logger.debug("Memory consolidation completed")

    def write(self, level: MemoryLevel, key: str, value: Any, expires_at: Optional[datetime] = None) -> None:
        now = datetime.now()

        if level == MemoryLevel.SCRATCHPAD:
            self._scratchpad[key] = {
                "value": value,
                "created_at": now,
                "accessed_at": now,
                "expires_at": expires_at,
            }
        elif level == MemoryLevel.WORKING:
            self._working[key] = {
                "value": value,
                "created_at": now,
                "accessed_at": now,
                "expires_at": expires_at,
            }
        else:
            if self._memory_store:
                self._memory_store.write(
                    MemoryItem(
                        level=level,
                        key=key,
                        value=value,
                        expires_at=expires_at,
                    )
                )

        logger.debug(f"Memory written: {level.value}/{key}")

    def read(self, level: MemoryLevel, key: str) -> Optional[Any]:
        if level == MemoryLevel.SCRATCHPAD:
            item = self._scratchpad.get(key)
            if item:
                item["accessed_at"] = datetime.now()
                return item["value"]
        elif level == MemoryLevel.WORKING:
            item = self._working.get(key)
            if item:
                item["accessed_at"] = datetime.now()
                return item["value"]
        else:
            if self._memory_store:
                items = self._memory_store.search(key)
                if items:
                    return items[0].get("value")

        return None

    def delete(self, level: MemoryLevel, key: str) -> bool:
        if level == MemoryLevel.SCRATCHPAD:
            if key in self._scratchpad:
                del self._scratchpad[key]
                return True
        elif level == MemoryLevel.WORKING:
            if key in self._working:
                del self._working[key]
                return True
        else:
            if self._memory_store:
                return self._memory_store.delete(key)

        return False

    def search(self, query: str, level: Optional[MemoryLevel] = None) -> List[Dict[str, Any]]:
        results = []

        if level is None or level == MemoryLevel.SCRATCHPAD:
            for key, item in self._scratchpad.items():
                if query.lower() in key.lower() or query.lower() in str(item["value"]).lower():
                    results.append({
                        "level": MemoryLevel.SCRATCHPAD.value,
                        "key": key,
                        "value": item["value"],
                        "accessed_at": item["accessed_at"],
                    })

        if level is None or level == MemoryLevel.WORKING:
            for key, item in self._working.items():
                if query.lower() in key.lower() or query.lower() in str(item["value"]).lower():
                    results.append({
                        "level": MemoryLevel.WORKING.value,
                        "key": key,
                        "value": item["value"],
                        "accessed_at": item["accessed_at"],
                    })

        if (level is None or level in [MemoryLevel.EPISODIC, MemoryLevel.SEMANTIC, MemoryLevel.PROCEDURAL]) and self._memory_store:
            store_results = self._memory_store.search(query)
            for result in store_results:
                results.append({
                    "level": result.get("level", "unknown"),
                    "key": result.get("key", ""),
                    "value": result.get("value"),
                    "accessed_at": result.get("accessed_at"),
                })

        results.sort(key=lambda x: x.get("accessed_at", datetime.min), reverse=True)
        return results

    def get_tick_time(self) -> float:
        return datetime.now().timestamp()

    def get_level_stats(self) -> Dict[str, int]:
        return {
            "scratchpad": len(self._scratchpad),
            "working": len(self._working),
            "persisted": self._memory_store.get_item_count() if self._memory_store else 0,
        }
