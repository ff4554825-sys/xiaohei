from typing import Dict, Any, Callable
from loguru import logger
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from ..types import Event, EventType


class MCPRequest(BaseModel):
    name: str
    args: Dict[str, Any]
    request_id: str


class MCPServer:
    def __init__(self, host: str = "localhost", port: int = 8080, event_bus=None):
        self._host = host
        self._port = port
        self._app = FastAPI()
        self._handlers: Dict[str, Callable] = {}
        self._event_bus = event_bus
        self._server = None
        self._setup_routes()
        logger.info(f"MCP Server initialized on {host}:{port}")

    def _setup_routes(self):
        @self._app.post("/call")
        async def call_tool(request: MCPRequest):
            result = await self._handle_call(request.name, request.args, request.request_id)
            return result

        @self._app.get("/health")
        async def health():
            return {"status": "healthy"}

        @self._app.get("/tools")
        async def list_tools():
            return {"tools": list(self._handlers.keys())}

    def register_handler(self, name: str, handler: Callable) -> None:
        self._handlers[name] = handler
        logger.info(f"MCP handler registered: {name}")

    async def _handle_call(self, name: str, args: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.TOOL_CALL,
                    payload={"request_id": request_id, "name": name},
                    source="mcp_server",
                )
            )

        handler = self._handlers.get(name)
        if not handler:
            return {"success": False, "error": f"Handler not found: {name}"}

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**args)
            else:
                result = handler(**args)

            if self._event_bus:
                self._event_bus.publish(
                    Event(
                        type=EventType.TOOL_RESULT,
                        payload={"request_id": request_id, "name": name, "success": True},
                        source="mcp_server",
                    )
                )

            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"MCP call failed: {name} - {e}")

            if self._event_bus:
                self._event_bus.publish(
                    Event(
                        type=EventType.ERROR,
                        payload={"request_id": request_id, "name": name, "error": str(e)},
                        source="mcp_server",
                    )
                )

            return {"success": False, "error": str(e)}

    async def start(self) -> None:
        config = uvicorn.Config(
            self._app,
            host=self._host,
            port=self._port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)
        await self._server.serve()

    async def stop(self) -> None:
        if self._server:
            await self._server.shutdown()
            logger.info("MCP Server stopped")
