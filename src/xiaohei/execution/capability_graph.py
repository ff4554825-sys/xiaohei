from typing import List, Dict, List, Any, Optional
from loguru import logger

from ..types import Capability


class CapabilityGraph:
    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._load_default_capabilities()
        logger.info("CapabilityGraph initialized with {} capabilities", len(self._capabilities))

    def _load_default_capabilities(self):
        capabilities = [
            Capability(
                name="web_search",
                description="Web search capability",
                skills=["search", "scrape"],
                dependencies=["network"],
            ),
            Capability(
                name="file_operations",
                description="File operations",
                skills=["read_file", "write_file", "delete_file"],
                dependencies=["filesystem"],
            ),
            Capability(
                name="code_execution",
                description="Code execution",
                skills=["python_run", "shell_exec"],
                dependencies=["sandbox"],
            ),
            Capability(
                name="data_processing",
                description="Data processing",
                skills=["parse_json", "transform_data", "csv_handling"],
                dependencies=[],
            ),
            Capability(
                name="llm_inference",
                description="LLM inference",
                skills=["generate_text", "summarize", "translate"],
                dependencies=["api_key"],
            ),
            Capability(
                name="task_planning",
                description="Task planning",
                skills=["decompose", "schedule", "prioritize"],
                dependencies=[],
            ),
            Capability(
                name="memory",
                description="Memory operations",
                skills=["read_memory", "write_memory", "search_memory"],
                dependencies=["database"],
            ),
            Capability(
                name="communication",
                description="Communication",
                skills=["send_message", "receive_message", "notify"],
                dependencies=["network"],
            ),
            Capability(
                name="authentication",
                description="Authentication",
                skills=["login", "verify_token", "authorize"],
                dependencies=["credentials"],
            ),
            Capability(
                name="monitoring",
                description="Monitoring",
                skills=["collect_metrics", "check_health", "alert"],
                dependencies=["logging"],
            ),
            Capability(
                name="governance",
                description="Governance",
                skills=["validate_policy", "audit", "enforce_rules"],
                dependencies=["policy_engine"],
            ),
            Capability(
                name="budget",
                description="Budget management",
                skills=["allocate", "check_budget", "report"],
                dependencies=["accounting"],
            ),
            Capability(
                name="caching",
                description="Caching",
                skills=["get_cache", "set_cache", "invalidate"],
                dependencies=["memory"],
            ),
            Capability(
                name="workflow",
                description="Workflow management",
                skills=["start_flow", "complete_step", "rollback"],
                dependencies=["state"],
            ),
            Capability(
                name="multimodal",
                description="Multimodal processing",
                skills=["image_process", "audio_process", "video_process"],
                dependencies=["models"],
            ),
            Capability(
                name="degradation",
                description="Degradation handling",
                skills=["degrade", "recover", "circuit_breaker"],
                dependencies=["monitoring"],
            ),
        ]

        for cap in capabilities:
            self._capabilities[cap.name] = cap

    def add_capability(self, capability: Capability) -> None:
        self._capabilities[capability.name] = capability
        logger.info(f"Capability added: {capability.name}")

    def get_capability(self, name: str) -> Optional[Capability]:
        return self._capabilities.get(name)

    def list_capabilities(self) -> List[Capability]:
        return list(self._capabilities.values())

    def find_route(self, from_cap: str, to_cap: str) -> Optional[List[str]]:
        visited = set()
        queue = [(from_cap, [from_cap])]

        while queue:
            current, path = queue.pop(0)

            if current == to_cap:
                return path

            if current in visited:
                continue

            visited.add(current)

            capability = self._capabilities.get(current)
            if capability:
                for dep in capability.dependencies:
                    if dep not in visited:
                        queue.append((dep, path + [dep]))

        return None

    def check_dependencies(self, capability_name: str) -> List[str]:
        capability = self._capabilities.get(capability_name)
        if not capability:
            return []

        return capability.dependencies

    def is_available(self, capability_name: str) -> bool:
        capability = self._capabilities.get(capability_name)
        if not capability:
            return False

        for dep in capability.dependencies:
            if dep not in self._capabilities:
                logger.warning(f"Capability {capability_name} missing dependency: {dep}")
                return False

        return True

    def get_fallback(self, capability_name: str) -> Optional[str]:
        capability = self._capabilities.get(capability_name)
        if capability:
            return capability.fallback
        return None
