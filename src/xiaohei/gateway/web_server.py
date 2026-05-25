from typing import Dict, Any
from loguru import logger
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import uvicorn
from uuid import UUID

from ..types import Task, TaskType, ExecutionResult
from ..control import FSMEngine, EventBus
from ..cognition import TaskParser, Planner, Critic, ControlDecider


class TaskRequest(BaseModel):
    input: str
    task_type: str = "information"
    context: Dict[str, Any] = {}


class WebServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 3721,
        fsm_engine: FSMEngine = None,
        event_bus: EventBus = None,
    ):
        self._host = host
        self._port = port
        self._app = FastAPI(title="XiaoHei Agent OS", version="1.0.0")
        self._fsm_engine = fsm_engine
        self._event_bus = event_bus
        self._task_parser = TaskParser(event_bus)
        self._planner = Planner(event_bus)
        self._critic = Critic(event_bus)
        self._control_decider = ControlDecider()
        self._setup_routes()
        logger.info(f"WebServer initialized on {host}:{port}")

    def _setup_routes(self):
        @self._app.post("/api/task")
        async def create_task(request: TaskRequest):
            try:
                task = self._task_parser.parse(request.input)
                task.context.update(request.context)

                if self._event_bus:
                    self._event_bus.publish(
                        {
                            "type": "task.created",
                            "payload": {"task_id": str(task.id), "input": request.input},
                        }
                    )

                return {"task_id": str(task.id), "type": task.type.value}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self._app.get("/api/task/{task_id}")
        async def get_task(task_id: str):
            return {"task_id": task_id, "status": "processing"}

        @self._app.post("/api/execute/{task_id}")
        async def execute_task(task_id: str):
            try:
                task = Task(
                    id=UUID(task_id),
                    type=TaskType.INFORMATION,
                    input="Test task",
                )

                plans = self._planner.diverge(task)
                scored_plans = self._planner.score(plans, task)
                selected_plan = self._planner.select(scored_plans)

                execution_result = ExecutionResult(
                    success=True,
                    output=f"Plan executed with score: {selected_plan.total_score}",
                    trace_id=task.id,
                )

                review = self._critic.review(task, execution_result.dict())
                decision = self._control_decider.decide(task, review)

                return {
                    "task_id": task_id,
                    "result": execution_result.dict(),
                    "review": review,
                    "decision": decision.dict(),
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self._app.get("/api/health")
        async def health():
            return {"status": "healthy", "version": "1.0.0"}

        @self._app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            try:
                while True:
                    data = await websocket.receive_json()
                    await websocket.send_json({"response": "Received: " + str(data)})
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")

    async def start(self):
        config = uvicorn.Config(
            self._app,
            host=self._host,
            port=self._port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()
