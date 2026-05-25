from typing import List, Dict, List, Any, Optional
from enum import Enum
from loguru import logger
from datetime import datetime, timedelta


class DegradationLevel(str, Enum):
    NORMAL = "normal"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


class DegradationChain:
    def __init__(self, name: str, levels: List[str], fallback: Optional[str] = None):
        self.name = name
        self.levels = levels
        self.fallback = fallback
        self.current_level = 0


class DegradationManager:
    def __init__(self):
        self._chains: Dict[str, DegradationChain] = {}
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._load_threshold = 0.8
        logger.info("DegradationManager initialized")

    def add_chain(self, name: str, levels: List[str], fallback: Optional[str] = None) -> None:
        self._chains[name] = DegradationChain(name, levels, fallback)
        logger.info(f"Degradation chain added: {name}")

    def get_chain(self, name: str) -> Optional[DegradationChain]:
        return self._chains.get(name)

    def degrade(self, name: str) -> bool:
        chain = self._chains.get(name)
        if not chain:
            logger.warning(f"Degradation chain not found: {name}")
            return False

        if chain.current_level < len(chain.levels) - 1:
            chain.current_level += 1
            logger.warning(f"Degraded {name} to level {chain.current_level}: {chain.levels[chain.current_level]}")
            return True

        if chain.fallback:
            logger.warning(f"Using fallback for {name}: {chain.fallback}")
            return True

        return False

    def recover(self, name: str) -> bool:
        chain = self._chains.get(name)
        if not chain:
            return False

        if chain.current_level > 0:
            chain.current_level -= 1
            logger.info(f"Recovered {name} to level {chain.current_level}: {chain.levels[chain.current_level]}")
            return True

        return False

    def get_level(self, name: str) -> DegradationLevel:
        chain = self._chains.get(name)
        if not chain:
            return DegradationLevel.NORMAL

        level = chain.current_level
        max_level = len(chain.levels) - 1

        if level == 0:
            return DegradationLevel.NORMAL
        elif level <= max_level * 0.5:
            return DegradationLevel.DEGRADED
        elif level <= max_level * 0.8:
            return DegradationLevel.CRITICAL
        else:
            return DegradationLevel.OFFLINE

    def trip_circuit_breaker(self, service: str, failure_count: int = 5) -> None:
        if service not in self._circuit_breakers:
            self._circuit_breakers[service] = {
                "tripped": False,
                "failure_count": 0,
                "last_failure": None,
                "cooldown_until": None,
            }

        breaker = self._circuit_breakers[service]
        breaker["failure_count"] += 1
        breaker["last_failure"] = datetime.now()

        if breaker["failure_count"] >= failure_count and not breaker["tripped"]:
            breaker["tripped"] = True
            breaker["cooldown_until"] = datetime.now() + timedelta(minutes=5)
            logger.error(f"Circuit breaker tripped for {service}")

    def reset_circuit_breaker(self, service: str) -> None:
        if service in self._circuit_breakers:
            self._circuit_breakers[service] = {
                "tripped": False,
                "failure_count": 0,
                "last_failure": None,
                "cooldown_until": None,
            }
            logger.info(f"Circuit breaker reset for {service}")

    def is_circuit_open(self, service: str) -> bool:
        breaker = self._circuit_breakers.get(service)
        if not breaker:
            return False

        if breaker["tripped"]:
            if breaker["cooldown_until"] and datetime.now() < breaker["cooldown_until"]:
                return True
            else:
                breaker["tripped"] = False
                return False

        return False

    def check_load(self, current_load: float) -> DegradationLevel:
        if current_load >= self._load_threshold * 1.2:
            return DegradationLevel.CRITICAL
        elif current_load >= self._load_threshold:
            return DegradationLevel.DEGRADED
        else:
            return DegradationLevel.NORMAL
