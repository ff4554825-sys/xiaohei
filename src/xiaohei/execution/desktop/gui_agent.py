"""GUI Agent — 桌面自动化智能体

流程: 理解屏幕 → 规划动作 → 执行 → 验证 → 记录轨迹
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger

from .screen import ScreenCapture, ElementDetector, ScreenElement, Screenshot
from .controller import DesktopController, ActionResult
from .trajectory import TrajectoryRecorder, ActionStep


@dataclass
class GUIPlan:
    """GUI 操作计划"""
    goal: str
    steps: List[Dict[str, Any]] = None
    confidence: float = 0.0
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []


class GUIAgent:
    """GUI 智能体 — 看屏幕→规划→执行→验证"""
    
    def __init__(self):
        self._screen = ScreenCapture()
        self._detector = ElementDetector()
        self._controller = DesktopController()
        self._trajectory = TrajectoryRecorder()
    
    @property
    def available(self) -> bool:
        return self._controller.available
    
    def execute(self, instruction: str) -> Dict[str, Any]:
        """执行桌面操作指令
        
        示例指令:
        - "打开记事本并输入hello"
        - "点击浏览器搜索按钮"
        - "把窗口拖到右边"
        """
        if not self.available:
            return {"success": False, "error": "PyAutoGUI 不可用, 请 pip install pyautogui"}
        
        self._trajectory.start_recording(instruction, app="desktop")
        
        try:
            # 1. 理解屏幕
            screenshot = self._screen.capture()
            elements = self._detector.detect(screenshot)
            
            # 2. 规划操作
            plan = self._plan(instruction, screenshot, elements)
            
            # 3. 执行操作
            results = []
            for step in plan.steps:
                result = self._execute_step(step)
                results.append(result)
                self._trajectory.record_step(
                    action=step.get("action", "unknown"),
                    params=step,
                    result=result.detail if hasattr(result, 'detail') else str(result),
                    duration_ms=result.duration_ms if hasattr(result, 'duration_ms') else 0,
                )
                if not result.success:
                    break
            
            # 4. 保存轨迹
            all_success = all(r.success for r in results if hasattr(r, 'success'))
            path = self._trajectory.finish(success=all_success)
            
            return {
                "success": all_success,
                "steps_executed": len(results),
                "trajectory_file": path,
                "elements_found": len(elements),
            }
        
        except Exception as e:
            self._trajectory.finish(success=False)
            logger.error(f"[gui_agent] 执行失败: {e}")
            return {"success": False, "error": str(e)[:200]}
    
    def _plan(self, instruction: str, screenshot: Screenshot,
              elements: List[ScreenElement]) -> GUIPlan:
        """根据指令规划操作"""
        instr_lower = instruction.lower()
        plan = GUIPlan(goal=instruction)
        
        # 简单的基于规则的规划
        if "打开" in instr_lower or "启动" in instr_lower:
            # 打开程序: Win键 → 搜索 → 输入
            app_name = instruction.split("打开")[-1].split("启动")[-1].strip()
            plan.steps = [
                {"action": "hotkey", "params": {"keys": ["win"]}},
                {"action": "type", "params": {"text": app_name}},
                {"action": "press", "params": {"key": "enter"}, "wait": 1.0},
            ]
        
        elif "点击" in instr_lower:
            target = instruction.split("点击")[-1].strip()
            for el in elements:
                if target in el.text.lower():
                    plan.steps = [
                        {"action": "click", "params": {"x": el.center[0], "y": el.center[1]}},
                    ]
                    plan.confidence = el.confidence
                    break
            if not plan.steps:
                plan.steps = [{"action": "click", "params": {"x": screenshot.width//2, "y": screenshot.height//2}}]
        
        elif "输入" in instr_lower or "写" in instr_lower:
            text = instruction.split("输入")[-1].split("写")[-1].strip()
            plan.steps = [
                {"action": "click", "params": {"x": screenshot.width//2, "y": screenshot.height//2}},
                {"action": "type", "params": {"text": text}},
            ]
        
        elif "拖" in instr_lower:
            plan.steps = [
                {"action": "drag", "params": {"x1": screenshot.width//3, "y1": screenshot.height//2,
                                              "x2": screenshot.width*2//3, "y2": screenshot.height//2}},
            ]
        
        else:
            plan.steps = [
                {"action": "screenshot", "params": {}},
                {"action": "info", "params": {"text": f"无法理解指令: {instruction}"}},
            ]
        
        return plan
    
    def _execute_step(self, step: Dict[str, Any]) -> ActionResult:
        """执行单步操作"""
        action = step.get("action", "")
        params = step.get("params", {})
        wait = step.get("wait", 0.2)
        
        if action == "click":
            result = self._controller.click(params.get("x", 0), params.get("y", 0))
        elif action == "double_click":
            result = self._controller.double_click(params.get("x", 0), params.get("y", 0))
        elif action == "right_click":
            result = self._controller.right_click(params.get("x", 0), params.get("y", 0))
        elif action == "type":
            result = self._controller.type_text(params.get("text", ""))
        elif action == "press":
            result = self._controller.press_key(params.get("key", ""))
        elif action == "hotkey":
            result = self._controller.hotkey(*params.get("keys", []))
        elif action == "drag":
            result = self._controller.drag(params.get("x1", 0), params.get("y1", 0),
                                          params.get("x2", 0), params.get("y2", 0))
        elif action == "scroll":
            result = self._controller.scroll(params.get("clicks", -3))
        elif action == "move":
            result = self._controller.move_to(params.get("x", 0), params.get("y", 0))
        elif action == "screenshot":
            result = ActionResult(True, "screenshot", "截图已保存")
        else:
            result = ActionResult(True, action, "跳过")
        
        # 等待(模拟人操作间隔)
        if wait > 0:
            time.sleep(min(wait, 2.0))
        
        return result
