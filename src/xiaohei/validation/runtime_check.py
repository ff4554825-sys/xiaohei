from typing import Dict, Any, Optional
from loguru import logger

from ..types import ExecutionResult, Event, EventType


class RuntimeCheck:
    def __init__(self, event_bus=None):
        self._event_bus = event_bus
        logger.info("RuntimeCheck initialized")

    def validate(self, result: ExecutionResult, expected_type: Optional[str] = None) -> Dict[str, Any]:
        checks = []

        checks.append(self._check_success(result))
        checks.append(self._check_output_type(result, expected_type))
        checks.append(self._check_error_handling(result))
        checks.append(self._check_performance(result))

        all_passed = all(c["passed"] for c in checks)

        if self._event_bus:
            if all_passed:
                self._event_bus.publish(
                    Event(
                        type=EventType.LOG,
                        payload={"message": "Runtime check passed"},
                        source="runtime_check",
                    )
                )
            else:
                self._event_bus.publish(
                    Event(
                        type=EventType.WARNING,
                        payload={"message": "Runtime check failed", "checks": checks},
                        source="runtime_check",
                    )
                )

        return {
            "passed": all_passed,
            "checks": checks,
        }

    def _check_success(self, result: ExecutionResult) -> Dict[str, Any]:
        passed = result.success
        return {
            "name": "success_check",
            "passed": passed,
            "message": "Execution succeeded" if passed else f"Execution failed: {result.error}",
        }

    def _check_output_type(self, result: ExecutionResult, expected_type: Optional[str]) -> Dict[str, Any]:
        if expected_type is None:
            return {
                "name": "output_type_check",
                "passed": True,
                "message": "No expected type specified",
            }

        output = result.output
        actual_type = type(output).__name__

        if expected_type.lower() == actual_type.lower():
            return {
                "name": "output_type_check",
                "passed": True,
                "message": f"Output type matches: {actual_type}",
            }

        return {
            "name": "output_type_check",
            "passed": False,
            "message": f"Expected type {expected_type}, got {actual_type}",
        }

    def _check_error_handling(self, result: ExecutionResult) -> Dict[str, Any]:
        if result.success:
            return {
                "name": "error_handling_check",
                "passed": True,
                "message": "No errors to handle",
            }

        if result.error:
            return {
                "name": "error_handling_check",
                "passed": True,
                "message": f"Error properly captured: {result.error}",
            }

        return {
            "name": "error_handling_check",
            "passed": False,
            "message": "Execution failed but no error message provided",
        }

    def _check_performance(self, result: ExecutionResult) -> Dict[str, Any]:
        metrics = result.metrics
        if not metrics:
            return {
                "name": "performance_check",
                "passed": True,
                "message": "No performance metrics available",
            }

        for metric in metrics:
            if metric.name == "duration" and metric.value > 30:
                return {
                    "name": "performance_check",
                    "passed": False,
                    "message": f"Execution took too long: {metric.value}s",
                }

        return {
            "name": "performance_check",
            "passed": True,
            "message": "Performance within acceptable limits",
        }
