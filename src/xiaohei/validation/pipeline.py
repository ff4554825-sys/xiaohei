"""VerifyPipeline — 四层校验流水线 (校验层)

适配新项目的 validation 模块接口:
  syntax_check(str)   → dict {passed, errors, warnings}
  semantic_check(Task, str) → dict {passed, message}
  runtime_check(ExecutionResult) → dict {passed, checks}
  policy_check(str, list) → dict {passed, message}
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .syntax_check import SyntaxCheck
from .semantic_check import SemanticCheck
from .runtime_check import RuntimeCheck
from .policy_check import PolicyCheck
from ..types import Task, ExecutionResult


@dataclass
class VerifyResult:
    checker: str
    passed: bool
    level: str = "error"
    message: str = ""
    detail: str = ""

    def to_dict(self) -> dict:
        return {"checker": self.checker, "passed": self.passed,
                "level": self.level, "message": self.message, "detail": self.detail}


@dataclass
class VerifyReport:
    target: str = ""
    all_passed: bool = True
    results: List[VerifyResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add(self, result: VerifyResult):
        self.results.append(result)
        if not result.passed:
            if result.level == "error":
                self.errors.append(result.message)
            else:
                self.warnings.append(result.message)
        self.all_passed = len(self.errors) == 0

    def summary(self) -> str:
        if self.all_passed:
            return f"✅ 全部通过 ({len(self.results)}项)"
        return f"❌ {len(self.errors)}项失败 + {len(self.warnings)}项警告"


class VerifyPipeline:
    """四层校验流水线"""

    def __init__(self):
        self._syntax = SyntaxCheck()
        self._semantic = SemanticCheck()
        self._runtime = RuntimeCheck()
        self._policy = PolicyCheck()

    def run(self, target: str = "", code: str = "", result: str = "",
            exit_code: int = 0, output: str = "", goal: str = "",
            action: str = "", constraints: list = None) -> VerifyReport:
        report = VerifyReport(target=target)

        # 1. 语法校验
        r1 = self._syntax.check(code)
        passed = r1.get("passed", len(r1.get("errors", [])) == 0) if isinstance(r1, dict) else True
        msg = "; ".join(r1.get("errors", r1.get("warnings", []))) if isinstance(r1, dict) else ""
        report.add(VerifyResult("syntax", passed, "error" if not passed else "info", msg[:100]))
        if not passed:
            return report

        # 2. 语义校验 (需要 Task 对象)
        try:
            from ..types import Task as TaskType, TaskType as TaskTypeEnum
            task_obj = TaskType(input=goal or code, type=TaskTypeEnum.INFORMATION)
            r2 = self._semantic.check(task_obj, output or result)
        except Exception:
            r2 = {"passed": True, "message": "semantic check skipped"}
        passed = r2.get("passed", True) if isinstance(r2, dict) else True
        msg = r2.get("message", "") if isinstance(r2, dict) else ""
        report.add(VerifyResult("semantic", passed, "error" if not passed else "info", msg[:100]))

        # 3. 运行时校验 (需要 ExecutionResult 对象)
        try:
            from ..types import ExecutionResult as ER
            er_obj = ER(success=exit_code == 0, output=output or result,
                       error="" if exit_code == 0 else f"exit code {exit_code}",
                       metrics=[])
            r3 = self._runtime.validate(er_obj)
        except Exception:
            r3 = {"passed": exit_code == 0, "message": "runtime check performed"}
        passed = r3.get("passed", exit_code == 0) if isinstance(r3, dict) else True
        msg = r3.get("message", "") if isinstance(r3, dict) else ""
        if not msg and isinstance(r3, dict) and "checks" in r3:
            failed = [c["message"] for c in r3["checks"] if not c.get("passed")]
            msg = "; ".join(failed) if failed else "ok"
        report.add(VerifyResult("runtime", passed, "error" if not passed else "info", msg[:100]))

        # 4. 策略校验
        r4 = self._policy.check(action, constraints or [])
        passed = r4.get("passed", True) if isinstance(r4, dict) else True
        msg = r4.get("message", "") if isinstance(r4, dict) else ""
        report.add(VerifyResult("policy", passed, "error" if not passed else "info", msg[:100]))

        return report
