from typing import List, Dict, List, Any, Optional, Protocol
from uuid import UUID
from loguru import logger
from datetime import datetime


class MemoryProvider(Protocol):
    def read(self, key: str) -> Optional[Any]:
        ...

    def write(self, key: str, value: Any) -> None:
        ...

    def delete(self, key: str) -> bool:
        ...

    def search(self, query: str) -> List[Dict[str, Any]]:
        ...


class ContextEngine:
    def __init__(self, providers: List[MemoryProvider] = []):
        self._providers: Dict[str, MemoryProvider] = {}
        self._active_provider: Optional[str] = None

        for provider in providers:
            name = type(provider).__name__
            self._providers[name] = provider
            if not self._active_provider:
                self._active_provider = name

        logger.info(f"ContextEngine initialized with {len(self._providers)} providers")

    def add_provider(self, name: str, provider: MemoryProvider) -> None:
        self._providers[name] = provider
        if not self._active_provider:
            self._active_provider = name
        logger.info(f"Memory provider added: {name}")

    def set_active_provider(self, name: str) -> bool:
        if name in self._providers:
            self._active_provider = name
            logger.info(f"Active provider set to: {name}")
            return True
        return False

    def get_provider(self, name: Optional[str] = None) -> Optional[MemoryProvider]:
        target_name = name or self._active_provider
        return self._providers.get(target_name)

    def gather_context(self, task_id: UUID, context_keys: List[str]) -> Dict[str, Any]:
        context: Dict[str, Any] = {}
        provider = self.get_provider()

        if not provider:
            logger.warning("No active memory provider")
            return context

        for key in context_keys:
            value = provider.read(key)
            if value is not None:
                context[key] = value

        logger.debug(f"Context gathered for task {task_id}: {len(context)} keys")
        return context

    def store_context(self, task_id: UUID, context: Dict[str, Any]) -> None:
        provider = self.get_provider()
        if not provider:
            logger.warning("No active memory provider")
            return

        for key, value in context.items():
            provider.write(key, value)

        logger.debug(f"Context stored for task {task_id}: {len(context)} keys")

    def search_context(self, query: str) -> List[Dict[str, Any]]:
        provider = self.get_provider()
        if not provider:
            logger.warning("No active memory provider")
            return []

        results = provider.search(query)
        logger.debug(f"Context search completed: {len(results)} results")
        return results

    def list_providers(self) -> List[str]:
        return list(self._providers.keys())
