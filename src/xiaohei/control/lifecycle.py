from typing import Dict, Any, Optional, Callable
from uuid import UUID
from loguru import logger
from datetime import datetime

from ..types import Checkpoint, Event, EventType


class LifecycleManager:
    def __init__(self, event_bus=None):
        self._checkpoints: Dict[UUID, Checkpoint] = {}
        self._event_bus = event_bus
        self._on_resume_callbacks: list[Callable[[Dict[str, Any]], Any]] = []
        logger.info("LifecycleManager initialized")

    def save_checkpoint(self, task_id: UUID, state: Dict[str, Any], memory_snapshot: Dict[str, Any]) -> Checkpoint:
        checkpoint = Checkpoint(
            task_id=task_id,
            state=state,
            memory_snapshot=memory_snapshot,
        )
        self._checkpoints[checkpoint.id] = checkpoint

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.CHECKPOINT,
                    payload={
                        "checkpoint_id": str(checkpoint.id),
                        "task_id": str(task_id),
                    },
                    source="lifecycle",
                )
            )

        logger.info(f"Checkpoint saved: {checkpoint.id} for task: {task_id}")
        return checkpoint

    def load_checkpoint(self, checkpoint_id: UUID) -> Optional[Checkpoint]:
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint:
            logger.info(f"Checkpoint loaded: {checkpoint_id}")
        return checkpoint

    def list_checkpoints(self, task_id: Optional[UUID] = None) -> list[Checkpoint]:
        if task_id:
            return [c for c in self._checkpoints.values() if c.task_id == task_id]
        return list(self._checkpoints.values())

    def delete_checkpoint(self, checkpoint_id: UUID) -> bool:
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            logger.info(f"Checkpoint deleted: {checkpoint_id}")
            return True
        return False

    def restore(self, checkpoint_id: UUID) -> Optional[Dict[str, Any]]:
        checkpoint = self.load_checkpoint(checkpoint_id)
        if not checkpoint:
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return None

        logger.info(f"Restoring from checkpoint: {checkpoint_id}")

        for callback in self._on_resume_callbacks:
            try:
                callback(checkpoint.state)
            except Exception as e:
                logger.error(f"Error during resume callback: {e}")

        return checkpoint.state

    def on_resume(self, callback: Callable[[Dict[str, Any]], Any]) -> None:
        self._on_resume_callbacks.append(callback)
        logger.debug("Resume callback registered")

    def get_latest_checkpoint(self, task_id: UUID) -> Optional[Checkpoint]:
        checkpoints = self.list_checkpoints(task_id)
        if not checkpoints:
            return None

        return max(checkpoints, key=lambda c: c.created_at)

    def cleanup_old_checkpoints(self, days_to_keep: int = 7) -> int:
        cutoff = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        old_ids = [
            c.id for c in self._checkpoints.values()
            if c.created_at.timestamp() < cutoff
        ]

        for id in old_ids:
            del self._checkpoints[id]

        logger.info(f"Cleaned up {len(old_ids)} old checkpoints")
        return len(old_ids)
