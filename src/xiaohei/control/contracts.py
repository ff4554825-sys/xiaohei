from typing import Dict, Any, Optional, Type
from loguru import logger
from pydantic import BaseModel


class ModuleContract(BaseModel):
    name: str
    interface: Dict[str, Any]
    version: str = "1.0.0"


class ModuleContracts:
    def __init__(self):
        self._contracts: Dict[str, ModuleContract] = {}
        self._register_default_contracts()
        logger.info("ModuleContracts initialized with {} contracts", len(self._contracts))

    def _register_default_contracts(self):
        contracts = [
            ModuleContract(
                name="fsm",
                interface={
                    "methods": ["transition", "get_current_phase", "reset"],
                    "events": ["phase.change"],
                },
            ),
            ModuleContract(
                name="event_bus",
                interface={
                    "methods": ["publish", "subscribe", "subscribe_wildcard"],
                    "events": ["*"],
                },
            ),
            ModuleContract(
                name="governance",
                interface={
                    "methods": ["evaluate", "add_rule", "remove_rule"],
                    "events": ["audit", "policy.violation"],
                },
            ),
            ModuleContract(
                name="policy",
                interface={
                    "methods": ["is_tool_allowed", "add_rule", "list_rules"],
                    "events": ["policy.violation"],
                },
            ),
            ModuleContract(
                name="budget",
                interface={
                    "methods": ["allocate", "check_budget", "get_usage"],
                    "events": ["budget.update"],
                },
            ),
            ModuleContract(
                name="task_parser",
                interface={
                    "methods": ["parse", "classify"],
                    "events": ["task.parsed"],
                },
            ),
            ModuleContract(
                name="planner",
                interface={
                    "methods": ["diverge", "score", "select"],
                    "events": ["plan.generated"],
                },
            ),
            ModuleContract(
                name="executor",
                interface={
                    "methods": ["execute", "cancel"],
                    "events": ["execution.start", "execution.end"],
                },
            ),
            ModuleContract(
                name="memory",
                interface={
                    "methods": ["read", "write", "delete", "search"],
                    "events": ["memory.access"],
                },
            ),
            ModuleContract(
                name="tool_registry",
                interface={
                    "methods": ["register", "unregister", "find"],
                    "events": ["tool.registered"],
                },
            ),
            ModuleContract(
                name="critic",
                interface={
                    "methods": ["review", "analyze"],
                    "events": ["critic.completed"],
                },
            ),
            ModuleContract(
                name="trace",
                interface={
                    "methods": ["start_span", "end_span", "record"],
                    "events": ["trace.span"],
                },
            ),
        ]

        for contract in contracts:
            self._contracts[contract.name] = contract

    def register_contract(self, contract: ModuleContract) -> None:
        self._contracts[contract.name] = contract
        logger.info(f"Module contract registered: {contract.name}")

    def get_contract(self, module_name: str) -> Optional[ModuleContract]:
        return self._contracts.get(module_name)

    def list_contracts(self) -> Dict[str, ModuleContract]:
        return dict(self._contracts)

    def validate_module(self, module_name: str, instance: Any) -> bool:
        contract = self.get_contract(module_name)
        if not contract:
            logger.warning(f"No contract found for module: {module_name}")
            return True

        for method_name in contract.interface.get("methods", []):
            if not hasattr(instance, method_name):
                logger.error(f"Module {module_name} missing required method: {method_name}")
                return False

        logger.debug(f"Module {module_name} validated successfully")
        return True
