from typing import List, Dict, Any, Optional, List
from loguru import logger
import asyncio
from datetime import datetime

from ..types import Event, EventType, Credential, ProviderType


class PlatformAdapter:
    def __init__(self, name: str, provider_type: ProviderType):
        self.name = name
        self.provider_type = provider_type
        self.connected = False

    async def connect(self):
        self.connected = True
        logger.info(f"Connected to {self.name}")

    async def disconnect(self):
        self.connected = False
        logger.info(f"Disconnected from {self.name}")

    async def send_message(self, user_id: str, message: str):
        pass

    async def receive_message(self) -> Optional[Dict[str, Any]]:
        return None


class Gateway:
    def __init__(self, credential_pool=None, event_bus=None):
        self._adapters: Dict[str, PlatformAdapter] = {}
        self._credential_pool = credential_pool
        self._event_bus = event_bus
        self._running = False
        logger.info("Gateway initialized")

    def register_adapter(self, name: str, adapter: PlatformAdapter) -> None:
        self._adapters[name] = adapter
        logger.info(f"Adapter registered: {name}")

    def unregister_adapter(self, name: str) -> bool:
        if name in self._adapters:
            del self._adapters[name]
            logger.info(f"Adapter unregistered: {name}")
            return True
        return False

    async def start(self) -> None:
        self._running = True
        logger.info("Gateway starting...")

        await asyncio.gather(
            *[adapter.connect() for adapter in self._adapters.values()]
        )

        asyncio.create_task(self._listen_loop())
        logger.info("Gateway started")

    async def stop(self) -> None:
        self._running = False
        await asyncio.gather(
            *[adapter.disconnect() for adapter in self._adapters.values()]
        )
        logger.info("Gateway stopped")

    async def _listen_loop(self):
        while self._running:
            for adapter in self._adapters.values():
                if adapter.connected:
                    try:
                        message = await adapter.receive_message()
                        if message:
                            await self._handle_message(adapter.name, message)
                    except Exception as e:
                        logger.error(f"Error receiving from {adapter.name}: {e}")

            await asyncio.sleep(1)

    async def _handle_message(self, platform: str, message: Dict[str, Any]):
        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "platform": platform,
                        "message": message,
                    },
                    source="gateway",
                )
            )

        logger.debug(f"Message from {platform}: {message}")

    def send(self, platform: str, user_id: str, message: str) -> bool:
        adapter = self._adapters.get(platform)
        if adapter and adapter.connected:
            asyncio.create_task(adapter.send_message(user_id, message))
            return True
        return False

    def list_platforms(self) -> List[str]:
        return list(self._adapters.keys())

    def get_status(self) -> Dict[str, Any]:
        status = {}
        for name, adapter in self._adapters.items():
            status[name] = {"connected": adapter.connected}
        return status
