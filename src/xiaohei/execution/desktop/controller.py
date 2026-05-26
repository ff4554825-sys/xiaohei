"""Desktop Controller — 桌面控制 (Desktop Automation)

用 PyAutoGUI 模拟键盘和鼠标操作。
"""

import time
from typing import Tuple, Optional, List
from dataclasses import dataclass
from loguru import logger


@dataclass
class ActionResult:
    """操作结果"""
    success: bool
    action: str
    detail: str = ""
    duration_ms: float = 0.0


class DesktopController:
    """桌面控制器 — 模拟键盘/鼠标/拖拽"""
    
    def __init__(self):
        self._pyautogui = None
        self._init_pyautogui()
    
    def _init_pyautogui(self):
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
            self._pyautogui = pyautogui
            logger.info("[desktop] PyAutoGUI 初始化成功")
        except ImportError:
            logger.warning("[desktop] PyAutoGUI 未安装, 桌面控制不可用")
    
    @property
    def available(self) -> bool:
        return self._pyautogui is not None
    
    # ── 鼠标 ──
    
    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> ActionResult:
        """点击坐标"""
        start = time.time()
        try:
            self._pyautogui.click(x, y, button=button, clicks=clicks)
            return ActionResult(True, f"click({x},{y})",
                               duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ActionResult(False, f"click({x},{y})", detail=str(e))
    
    def double_click(self, x: int, y: int) -> ActionResult:
        return self.click(x, y, clicks=2)
    
    def right_click(self, x: int, y: int) -> ActionResult:
        return self.click(x, y, button="right")
    
    def move_to(self, x: int, y: int, duration: float = 0.2) -> ActionResult:
        """移动鼠标到坐标"""
        start = time.time()
        try:
            self._pyautogui.moveTo(x, y, duration=duration)
            return ActionResult(True, f"move({x},{y})",
                               duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ActionResult(False, f"move({x},{y})", detail=str(e))
    
    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.3) -> ActionResult:
        """拖拽: 从(x1,y1)到(x2,y2)"""
        start = time.time()
        try:
            self._pyautogui.moveTo(x1, y1)
            self._pyautogui.drag(x2 - x1, y2 - y1, duration=duration)
            return ActionResult(True, f"drag({x1},{y1}→{x2},{y2})",
                               duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ActionResult(False, f"drag", detail=str(e))
    
    # ── 键盘 ──
    
    def type_text(self, text: str, interval: float = 0.05) -> ActionResult:
        """输入文本"""
        start = time.time()
        try:
            self._pyautogui.write(text, interval=interval)
            return ActionResult(True, f"type({len(text)} chars)",
                               duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ActionResult(False, f"type", detail=str(e))
    
    def press_key(self, key: str) -> ActionResult:
        """按单个键(enter/tab/esc/...)"""
        start = time.time()
        try:
            self._pyautogui.press(key)
            return ActionResult(True, f"press({key})",
                               duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ActionResult(False, f"press({key})", detail=str(e))
    
    def hotkey(self, *keys: str) -> ActionResult:
        """组合键(ctrl+c, alt+tab...)"""
        start = time.time()
        try:
            self._pyautogui.hotkey(*keys)
            return ActionResult(True, f"hotkey({'+'.join(keys)})",
                               duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ActionResult(False, f"hotkey", detail=str(e))
    
    def scroll(self, clicks: int = -3) -> ActionResult:
        """滚轮"""
        start = time.time()
        try:
            self._pyautogui.scroll(clicks)
            return ActionResult(True, f"scroll({clicks})",
                               duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ActionResult(False, f"scroll", detail=str(e))
    
    # ── 定位元素 ──
    
    def locate_on_screen(self, image_path: str, confidence: float = 0.9) -> Optional[Tuple[int, int, int, int]]:
        """在屏幕上查找图片,返回坐标"""
        try:
            result = self._pyautogui.locateOnScreen(image_path, confidence=confidence)
            return result
        except Exception:
            return None
    
    def get_position(self) -> Tuple[int, int]:
        """获取当前鼠标位置"""
        return self._pyautogui.position()
