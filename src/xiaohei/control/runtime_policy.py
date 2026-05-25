from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime, timedelta

from ..types import RuntimeMode, ModuleStatus


class RuntimePolicy:
    def __init__(self):
        self._module_status: Dict[str, ModuleStatus] = {}
        self._mode: RuntimeMode = RuntimeMode.WARM
        self._state_compression_threshold = 1000
        self._last_check = datetime.now()
        logger.info("RuntimePolicy initialized")

    def set_mode(self, mode: RuntimeMode) -> None:
        self._mode = mode
        logger.info(f"Runtime mode changed to: {mode}")

    def get_mode(self) -> RuntimeMode:
        return self._mode

    def update_module_status(self, module_name: str, status: str, metrics: Dict[str, Any] = {}) -> None:
        if module_name not in self._module_status:
            self._module_status[module_name] = ModuleStatus(name=module_name)

        self._module_status[module_name].status = status
        self._module_status[module_name].metrics = metrics
        self._module_status[module_name].mode = self._mode

        if status != "running":
            logger.warning(f"Module {module_name} status changed to: {status}")

    def get_module_status(self, module_name: str) -> Optional[ModuleStatus]:
        return self._module_status.get(module_name)

    def list_module_statuses(self) -> Dict[str, ModuleStatus]:
        return dict(self._module_status)

    def compress_state(self) -> Dict[str, Any]:
        compressed = {}
        total_size = 0

        for name, status in self._module_status.items():
            metrics_size = len(str(status.metrics))
            total_size += metrics_size

            if metrics_size > self._state_compression_threshold:
                compressed[name] = {
                    "status": status.status,
                    "mode": status.mode.value,
                    "metrics_count": len(status.metrics),
                    "compressed": True,
                }
            else:
                compressed[name] = {
                    "status": status.status,
                    "mode": status.mode.value,
                    "metrics": status.metrics,
                    "compressed": False,
                }

        logger.debug(f"State compressed, total size: {total_size}")
        return compressed

    def check_health(self) -> Dict[str, Any]:
        now = datetime.now()
        if (now - self._last_check).total_seconds() > 30:
            self._last_check = now

            for name, status in self._module_status.items():
                if status.status != "running":
                    logger.warning(f"Health check: {name} is not running")

        return {
            "mode": self._mode.value,
            "modules": len(self._module_status),
            "healthy": all(s.status == "running" for s in self._module_status.values()),
            "timestamp": now.isoformat(),
        }

    def can_execute(self, module_name: str) -> bool:
        status = self.get_module_status(module_name)
        if not status:
            return True

        if self._mode == RuntimeMode.COLD:
            return False
        if self._mode == RuntimeMode.WARM:
            return status.status == "running"

        return True
