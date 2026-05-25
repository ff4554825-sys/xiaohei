from typing import Dict, Any
from loguru import logger

from ..types import Event, EventType


class SyntaxCheck:
    def __init__(self, event_bus=None):
        self._event_bus = event_bus
        logger.info("SyntaxCheck initialized")

    def check(self, code: str, language: str = "python") -> Dict[str, Any]:
        errors = []
        warnings = []

        if language == "python":
            errors, warnings = self._check_python(code)
        elif language == "json":
            errors, warnings = self._check_json(code)
        elif language == "yaml":
            errors, warnings = self._check_yaml(code)
        elif language == "shell":
            errors, warnings = self._check_shell(code)

        if self._event_bus and errors:
            self._event_bus.publish(
                Event(
                    type=EventType.ERROR,
                    payload={"message": f"Syntax errors found: {len(errors)}"},
                    source="syntax_check",
                )
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _check_python(self, code: str) -> tuple:
        errors = []
        warnings = []

        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            errors.append(f"Line {e.lineno}: {e.msg}")
        except Exception as e:
            errors.append(str(e))

        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                warnings.append(f"Line {i}: Line too long")
            if line.strip().startswith("print "):
                warnings.append(f"Line {i}: Using print statement instead of function")

        return errors, warnings

    def _check_json(self, code: str) -> tuple:
        errors = []
        warnings = []

        try:
            import json

            json.loads(code)
        except json.JSONDecodeError as e:
            errors.append(f"Line {e.lineno}: {e.msg}")

        return errors, warnings

    def _check_yaml(self, code: str) -> tuple:
        errors = []
        warnings = []

        try:
            import yaml

            yaml.safe_load(code)
        except yaml.YAMLError as e:
            errors.append(str(e))

        return errors, warnings

    def _check_shell(self, code: str) -> tuple:
        errors = []
        warnings = []

        dangerous_commands = ["rm -rf", "dd if=", "mkfs", "format"]
        for cmd in dangerous_commands:
            if cmd in code:
                warnings.append(f"Potentially dangerous command: {cmd}")

        return errors, warnings
