"""ErrorHandler — 模块边界异常防护 (控制平面)

确保每个模块的错误不会级联崩溃整个系统。
提供统一的安全调用包装器。
"""

import functools
import time
import traceback
from typing import Callable, Any, Optional
from loguru import logger


class ModuleError(Exception):
    """模块级异常基类"""
    def __init__(self, module: str, message: str, original: Optional[Exception] = None):
        self.module = module
        self.original = original
        super().__init__(f"[{module}] {message}")


class SafetyBoundary:
    """安全边界 — 模块调用的防护层"""
    
    # 每个模块的默认返回值(当调用失败时)
    FALLBACKS = {
        "task_parser": None,
        "planner": [],
        "failure_classifier": {"failure_type": "unknown", "recovery": "retry"},
        "critic": {"score": 0, "valid": True, "issues": []},
        "control_decider": {"decision": "continue"},
        "governance": {"passed": True, "blocks": [], "warnings": []},
        "event_bus": None,
        "memory_os": None,
        "capability_graph": [],
        "sandbox": {"allowed": True},
        "verify": {"all_passed": True, "results": []},
        "trace": None,
        "metrics": None,
    }
    
    @classmethod
    def protect(cls, module_name: str, fallback: Any = None):
        """装饰器: 安全保护模块函数
        
        用法:
            @SafetyBoundary.protect("task_parser")
            def parse(text): ...
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    fb = fallback if fallback is not None else cls.FALLBACKS.get(module_name)
                    logger.error(f"[{module_name}] 异常: {e}")
                    logger.debug(traceback.format_exc())
                    return fb
            return wrapper
        return decorator
    
    @staticmethod
    def safe_call(module: str, func: Callable, *args, **kwargs) -> Any:
        """安全调用: 函数级别异常捕获"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"[{module}] safe_call 失败: {e}")
            return None


# ── 全局注册表: 各模块的安全调用点 ──

class ModuleRegistry:
    """模块注册表 — 统一管理模块的安全调用"""
    
    def __init__(self):
        self._modules = {}
    
    def register(self, name: str, module: Any):
        self._modules[name] = module
    
    def get(self, name: str) -> Any:
        return self._modules.get(name)
    
    def safe_call(self, module_name: str, method: str, *args, **kwargs) -> Any:
        """通过注册表安全调用模块方法"""
        mod = self._modules.get(module_name)
        if not mod:
            logger.warning(f"[registry] 模块未注册: {module_name}")
            return SafetyBoundary.FALLBACKS.get(module_name)
        
        func = getattr(mod, method, None)
        if not func:
            logger.warning(f"[registry] 方法不存在: {module_name}.{method}")
            return SafetyBoundary.FALLBACKS.get(module_name)
        
        return SafetyBoundary.safe_call(f"{module_name}.{method}", func, *args, **kwargs)


_registry = ModuleRegistry()


def get_registry() -> ModuleRegistry:
    return _registry
