from typing import List, Dict, List, Any, Optional
from uuid import UUID
from loguru import logger
import json
import os

from ..types import Checkpoint, Event, EventType


class DynamicReplay:
    def __init__(self, data_dir: str = "./data/replays", event_bus=None):
        self._data_dir = data_dir
        self._event_bus = event_bus
        os.makedirs(data_dir, exist_ok=True)
        logger.info("DynamicReplay initialized")

    def record(self, task_id: UUID, events: List[Event]) -> None:
        replay_data = {
            "task_id": str(task_id),
            "events": [self._event_to_dict(e) for e in events],
            "recorded_at": events[-1].timestamp.isoformat() if events else "",
        }

        filepath = os.path.join(self._data_dir, f"{task_id}.json")
        with open(filepath, "w") as f:
            json.dump(replay_data, f, indent=2)

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.REPLAY,
                    payload={"task_id": str(task_id), "event_count": len(events)},
                    source="replay",
                )
            )

        logger.info(f"Replay recorded for task: {task_id}")

    def _event_to_dict(self, event: Event) -> Dict[str, Any]:
        return {
            "id": str(event.id),
            "type": event.type.value if isinstance(event.type, EventType) else str(event.type),
            "payload": event.payload,
            "timestamp": event.timestamp.isoformat(),
            "source": event.source,
        }

    def replay(self, task_id: UUID, speed: float = 1.0) -> bool:
        filepath = os.path.join(self._data_dir, f"{task_id}.json")
        if not os.path.exists(filepath):
            logger.error(f"Replay file not found: {task_id}")
            return False

        try:
            with open(filepath, "r") as f:
                replay_data = json.load(f)

            events = [self._dict_to_event(e) for e in replay_data["events"]]

            if self._event_bus:
                for event in events:
                    self._event_bus.publish(event)

            logger.info(f"Replay completed for task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to replay task {task_id}: {e}")
            return False

    def _dict_to_event(self, data: Dict[str, Any]) -> Event:
        return Event(
            id=UUID(data["id"]),
            type=EventType(data["type"]) if data["type"] in EventType.__members__ else data["type"],
            payload=data["payload"],
            timestamp=data["timestamp"],
            source=data["source"],
        )

    def list_replays(self) -> List[Dict[str, Any]]:
        replays = []

        for filename in os.listdir(self._data_dir):
            if filename.endswith(".json"):
                task_id = os.path.splitext(filename)[0]
                filepath = os.path.join(self._data_dir, filename)

                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                        replays.append({
                            "task_id": task_id,
                            "event_count": len(data.get("events", [])),
                            "recorded_at": data.get("recorded_at", ""),
                        })
                except Exception as e:
                    logger.error(f"Failed to read replay file {filename}: {e}")

        return replays

    def delete_replay(self, task_id: UUID) -> bool:
        filepath = os.path.join(self._data_dir, f"{task_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Replay deleted: {task_id}")
            return True
        return False
