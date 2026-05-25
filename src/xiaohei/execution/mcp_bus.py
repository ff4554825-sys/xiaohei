from typing import List, Dict, List, Any, Optional, Callable
from uuid import UUID, uuid4
import asyncio
from loguru import logger

from ..types import Event, EventType


class MCPBus:
    def __init__(self, event_bus=None):
        self._local_handlers: Dict[str, Callable] = {}
        self._mcp_clients: Dict[str, Any] = {}
        self._remote_agents: Dict[str, Any] = {}
        self._event_bus = event_bus
        logger.info("MCPBus initialized")

    def register_local_handler(self, name: str, handler: Callable) -> None:
        self._local_handlers[name] = handler
        logger.info(f"Local handler registered: {name}")

    def register_mcp_client(self, name: str, client: Any) -> None:
        self._mcp_clients[name] = client
        logger.info(f"MCP client registered: {name}")

    def register_remote_agent(self, name: str, endpoint: str) -> None:
        self._remote_agents[name] = {"endpoint": endpoint, "active": True}
        logger.info(f"Remote agent registered: {name} -> {endpoint}")

    async def call(self, name: str, args: Dict[str, Any], layer: str = "auto") -> Dict[str, Any]:
        request_id = str(uuid4())

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.TOOL_CALL,
                    payload={
                        "request_id": request_id,
                        "name": name,
                        "layer": layer,
                    },
                    source="mcp_bus",
                )
            )

        if layer == "local" or (layer == "auto" and name in self._local_handlers):
            return await self._call_local(name, args, request_id)
        elif layer == "mcp" or (layer == "auto" and name in self._mcp_clients):
            return await self._call_mcp(name, args, request_id)
        elif layer == "remote" or (layer == "auto" and name in self._remote_agents):
            return await self._call_remote(name, args, request_id)

        return {"success": False, "error": f"Handler not found: {name}"}

    async def _call_local(self, name: str, args: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        try:
            handler = self._local_handlers[name]
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**args)
            else:
                result = handler(**args)

            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Local call failed: {name} - {e}")
            return {"success": False, "error": str(e)}

    async def _call_mcp(self, name: str, args: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        client = self._mcp_clients.get(name)
        if not client:
            return {"success": False, "error": f"MCP client not found: {name}"}

        try:
            result = await client.call(name, args)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"MCP call failed: {name} - {e}")
            return {"success": False, "error": str(e)}

    async def _call_remote(self, name: str, args: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        agent = self._remote_agents.get(name)
        if not agent or not agent["active"]:
            return {"success": False, "error": f"Remote agent not available: {name}"}

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    agent["endpoint"],
                    json={"name": name, "args": args, "request_id": request_id},
                    timeout=30,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Remote call failed: {name} - {e}")
            return {"success": False, "error": str(e)}

    def list_handlers(self, layer: Optional[str] = None) -> List[Dict[str, Any]]:
        handlers = []

        if layer is None or layer == "local":
            for name in self._local_handlers:
                handlers.append({"name": name, "layer": "local"})

        if layer is None or layer == "mcp":
            for name in self._mcp_clients:
                handlers.append({"name": name, "layer": "mcp"})

        if layer is None or layer == "remote":
            for name, agent in self._remote_agents.items():
                handlers.append({"name": name, "layer": "remote", "endpoint": agent["endpoint"]})

        return handlers

    def get_route(self, name: str) -> Optional[str]:
        if name in self._local_handlers:
            return "local"
        elif name in self._mcp_clients:
            return "mcp"
        elif name in self._remote_agents:
            return "remote"
        return None
