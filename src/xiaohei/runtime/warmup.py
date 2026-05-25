"""Warmup — 冷启动优化 (运行时内核)

预加载关键模块, 减少首次请求延迟。
"""

import sys
import os
import threading
import time
from pathlib import Path
from loguru import logger


def preload_modules():
    """预加载关键模块(后台线程, 不阻塞)"""
    modules = [
        "src.xiaohei.types",
        "src.xiaohei.control.fsm",
        "src.xiaohei.control.event_bus",
        "src.xiaohei.control.governance",
        "src.xiaohei.cognition.task_parser",
        "src.xiaohei.cognition.planner",
        "src.xiaohei.cognition.failure_classifier",
        "src.xiaohei.cognition.control_decider",
        "src.xiaohei.execution.executor",
        "src.xiaohei.data.memory_os",
        "src.xiaohei.data.ticker",
        "src.xiaohei.validation.pipeline",
        "src.xiaohei.runtime.agent_os",
    ]
    
    start = time.time()
    loaded = 0
    for mod_name in modules:
        try:
            __import__(mod_name)
            loaded += 1
        except Exception as e:
            logger.debug(f"[warmup] 跳过 {mod_name}: {e}")
    
    elapsed = (time.time() - start) * 1000
    logger.info(f"[warmup] 预加载 {loaded}/{len(modules)} 模块, 耗时 {elapsed:.0f}ms")


def warmup():
    """执行预热(异步)"""
    thread = threading.Thread(target=preload_modules, daemon=True)
    thread.start()
