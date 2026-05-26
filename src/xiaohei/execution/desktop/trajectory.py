"""Action Trajectory — 操作轨迹记录与回放 (Desktop Automation)

记录一系列桌面操作, 支持回放和轨迹学习。
"""

import json
import time
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger

TRAJECTORY_DIR = Path.home() / ".xiaohei" / "trajectories"


@dataclass
class ActionStep:
    """单步操作"""
    action: str       # click / type / press / drag / scroll / hotkey / screenshot
    params: dict = field(default_factory=dict)
    result: str = ""
    timestamp: float = 0.0
    duration_ms: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "params": {k: v for k, v in self.params.items() if k != "password"},
            "result": self.result[:100],
            "duration_ms": round(self.duration_ms, 1),
        }


@dataclass
class ActionTrajectory:
    """完整的操作轨迹"""
    task: str
    steps: List[ActionStep] = field(default_factory=list)
    success: bool = False
    start_time: float = 0.0
    end_time: float = 0.0
    app: str = ""
    
    def add_step(self, step: ActionStep):
        self.steps.append(step)
    
    @property
    def total_duration(self) -> float:
        return self.end_time - self.start_time if self.end_time > self.start_time else 0
    
    def to_dict(self) -> dict:
        return {
            "task": self.task[:100],
            "app": self.app,
            "success": self.success,
            "steps": [s.to_dict() for s in self.steps],
            "total_steps": len(self.steps),
            "duration": round(self.total_duration, 1),
        }


class TrajectoryRecorder:
    """操作轨迹记录器"""
    
    def __init__(self):
        TRAJECTORY_DIR.mkdir(parents=True, exist_ok=True)
        self._current: Optional[ActionTrajectory] = None
    
    def start_recording(self, task: str, app: str = ""):
        """开始记录轨迹"""
        self._current = ActionTrajectory(
            task=task, app=app, start_time=time.time()
        )
        logger.info(f"[trajectory] 开始记录: {task[:40]}")
    
    def record_step(self, action: str, params: dict = None,
                    result: str = "", duration_ms: float = 0.0):
        """记录单步操作"""
        if not self._current:
            return
        step = ActionStep(
            action=action,
            params=params or {},
            result=result,
            timestamp=time.time(),
            duration_ms=duration_ms,
        )
        self._current.add_step(step)
    
    def finish(self, success: bool = True) -> Optional[str]:
        """完成记录,保存到磁盘"""
        if not self._current:
            return None
        self._current.end_time = time.time()
        self._current.success = success
        
        # 保存
        filename = f"{int(time.time())}_{self._current.app or 'desktop'}.json"
        path = TRAJECTORY_DIR / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._current.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"[trajectory] 已保存: {path.name} ({len(self._current.steps)}步)")
        self._current = None
        return str(path)
    
    def load(self, path: str) -> Optional[ActionTrajectory]:
        """从文件加载轨迹"""
        try:
            with open(path, "r") as f:
                data = json.load(f)
            t = ActionTrajectory(task=data.get("task", ""), app=data.get("app", ""),
                               success=data.get("success", False),
                               start_time=data.get("start_time", 0),
                               end_time=data.get("end_time", 0))
            for s in data.get("steps", []):
                t.add_step(ActionStep(**s))
            return t
        except Exception as e:
            logger.error(f"[trajectory] 加载失败: {e}")
            return None
    
    def list_trajectories(self) -> List[dict]:
        """列出所有轨迹"""
        results = []
        for f in sorted(TRAJECTORY_DIR.glob("*.json"), reverse=True)[:20]:
            try:
                data = json.loads(f.read_text())
                results.append({
                    "file": f.name,
                    "task": data.get("task", "")[:50],
                    "steps": data.get("total_steps", 0),
                    "success": data.get("success", False),
                    "time": f.stat().st_mtime,
                })
            except Exception:
                continue
        return results
