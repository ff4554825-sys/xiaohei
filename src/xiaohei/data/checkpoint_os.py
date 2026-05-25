from typing import List, Dict, List, Any, Optional
from uuid import UUID
from loguru import logger
from datetime import datetime
import json
import os

from ..types import Checkpoint, Event, EventType


class CheckpointOS:
    def __init__(self, data_dir: str = "./data/checkpoints", event_bus=None):
        self._data_dir = data_dir
        self._checkpoints: Dict[UUID, Checkpoint] = {}
        self._event_bus = event_bus
        os.makedirs(data_dir, exist_ok=True)
        self._load_checkpoints()
        logger.info("CheckpointOS initialized")

    def _load_checkpoints(self):
        for filename in os.listdir(self._data_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self._data_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                        checkpoint = Checkpoint(
                            id=UUID(data["id"]),
                            task_id=UUID(data["task_id"]),
                            state=data["state"],
                            memory_snapshot=data["memory_snapshot"],
                            created_at=datetime.fromisoformat(data["created_at"]),
                        )
                        self._checkpoints[checkpoint.id] = checkpoint
                except Exception as e:
                    logger.error(f"Failed to load checkpoint {filename}: {e}")

        logger.info(f"Loaded {len(self._checkpoints)} checkpoints")

    def save(self, task_id: UUID, state: Dict[str, Any], memory_snapshot: Dict[str, Any]) -> Checkpoint:
        checkpoint = Checkpoint(
            task_id=task_id,
            state=state,
            memory_snapshot=memory_snapshot,
        )

        self._checkpoints[checkpoint.id] = checkpoint

        filepath = os.path.join(self._data_dir, f"{checkpoint.id}.json")
        with open(filepath, "w") as f:
            json.dump({
                "id": str(checkpoint.id),
                "task_id": str(checkpoint.task_id),
                "state": checkpoint.state,
                "memory_snapshot": checkpoint.memory_snapshot,
                "created_at": checkpoint.created_at.isoformat(),
            }, f, indent=2)

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.CHECKPOINT,
                    payload={
                        "checkpoint_id": str(checkpoint.id),
                        "task_id": str(task_id),
                    },
                    source="checkpoint_os",
                )
            )

        logger.info(f"Checkpoint saved: {checkpoint.id}")
        return checkpoint

    def load(self, checkpoint_id: UUID) -> Optional[Checkpoint]:
        return self._checkpoints.get(checkpoint_id)

    def list(self, task_id: Optional[UUID] = None) -> List[Checkpoint]:
        if task_id:
            return [c for c in self._checkpoints.values() if c.task_id == task_id]
        return list(self._checkpoints.values())

    def delete(self, checkpoint_id: UUID) -> bool:
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint:
            del self._checkpoints[checkpoint_id]

            filepath = os.path.join(self._data_dir, f"{checkpoint_id}.json")
            if os.path.exists(filepath):
                os.remove(filepath)

            logger.info(f"Checkpoint deleted: {checkpoint_id}")
            return True
        return False

    def rollback(self, checkpoint_id: UUID) -> Optional[Dict[str, Any]]:
        checkpoint = self.load(checkpoint_id)
        if not checkpoint:
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return None

        logger.info(f"Rolling back to checkpoint: {checkpoint_id}")
        return checkpoint.state

    def get_history(self, task_id: UUID) -> List[Checkpoint]:
        checkpoints = self.list(task_id)
        checkpoints.sort(key=lambda c: c.created_at)
        return checkpoints

    def cleanup_old(self, days_to_keep: int = 7) -> int:
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        old_checkpoints = [
            c for c in self._checkpoints.values()
            if c.created_at < cutoff
        ]

        for checkpoint in old_checkpoints:
            self.delete(checkpoint.id)

        logger.info(f"Cleaned up {len(old_checkpoints)} old checkpoints")
        return len(old_checkpoints)
