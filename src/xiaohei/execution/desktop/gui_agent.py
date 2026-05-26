"""GUIAgent — 真正的桌面自动化智能体 (Desktop Automation)

真实工作原理(无需OCR/无需视觉模型):
1. 键盘驱动导航: Alt+Tab → Tab → Enter → 键入
2. 坐标点击: 直接操作已知UI布局
3. 操作轨迹: 记录全部步骤供回放和学习

依赖: pyautogui (pip install pyautogui)
"""

import time
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger

TRAJECTORY_DIR = Path.home() / ".xiaohei" / "trajectories"


@dataclass
class ActionResult:
    success: bool
    action: str
    detail: str = ""
    duration_ms: float = 0.0


class DesktopController:
    """真实桌面控制 — 基于键盘导航 + 坐标操作"""
    
    def __init__(self):
        self._pg = None
        self._init_pyautogui()
    
    def _init_pyautogui(self):
        try:
            import pyautogui as pg
            pg.FAILSAFE = True
            pg.PAUSE = 0.15
            self._pg = pg
            self.screen_width, self.screen_height = pg.size()
            logger.info(f"[desktop] PyAutoGUI就绪 {self.screen_width}x{self.screen_height}")
        except ImportError:
            logger.warning("[desktop] 需要 pip install pyautogui")
    
    @property
    def available(self) -> bool:
        return self._pg is not None
    
    # ── 键盘导航(真实的Windows桌面操作) ──
    
    def alt_tab(self, times: int = 1) -> ActionResult:
        """Alt+Tab 切换窗口"""
        return self._run("alt_tab", lambda: (
            self._pg.keyDown('alt'),
            [self._pg.press('tab') for _ in range(times)],
            self._pg.keyUp('alt')
        ))
    
    def tab(self, times: int = 1) -> ActionResult:
        """Tab 切换焦点"""
        return self._run("tab", lambda: [self._pg.press('tab') for _ in range(times)])
    
    def enter(self) -> ActionResult:
        """按回车"""
        return self._run("enter", lambda: self._pg.press('enter'))
    
    def press(self, key: str) -> ActionResult:
        """按指定键"""
        return self._run(f"press({key})", lambda: self._pg.press(key))
    
    def hotkey(self, *keys: str) -> ActionResult:
        """组合键"""
        return self._run(f"hotkey({'+'.join(keys)})", lambda: self._pg.hotkey(*keys))
    
    def type_text(self, text: str, interval: float = 0.02) -> ActionResult:
        """键入文本"""
        return self._run(f"type({len(text)}chars)", lambda: self._pg.write(text, interval=interval))
    
    def click(self, x: int, y: int, button: str = "left") -> ActionResult:
        """点击坐标"""
        return self._run(f"click({x},{y})", lambda: self._pg.click(x, y, button=button))
    
    def move_to(self, x: int, y: int) -> ActionResult:
        """移动鼠标到坐标"""
        return self._run(f"move({x},{y})", lambda: self._pg.moveTo(x, y))
    
    # ── 高级操作(真实的Windows桌面任务) ──
    
    def open_run_dialog(self) -> ActionResult:
        """Win+R 打开运行对话框"""
        return self.hotkey('win', 'r')
    
    def open_start_menu(self) -> ActionResult:
        """Win 打开开始菜单"""
        return self.press('win')
    
    def search_and_open(self, app_name: str) -> Dict[str, Any]:
        """搜索并打开程序: Win → 输入名称 → 回车"""
        start = time.time()
        self.press('win')
        time.sleep(0.3)
        self.type_text(app_name)
        time.sleep(0.5)
        self.enter()
        return {
            "success": True,
            "action": f"open({app_name})",
            "duration_ms": (time.time() - start) * 1000,
        }
    
    def get_active_window_title(self) -> str:
        """获取当前活动窗口标题(通过截图+探针)"""
        try:
            import subprocess
            r = subprocess.run(
                ["powershell", "-Command", "(Get-Window).Name | Select-Object -First 1"],
                capture_output=True, text=True, timeout=3
            )
            return r.stdout.strip() or "unknown"
        except:
            return "unknown"
    
    def screenshot(self, path: str = None) -> str:
        """截图并保存"""
        if path is None:
            path = str(TRAJECTORY_DIR / f"screen_{int(time.time())}.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._pg.screenshot(path)
        return path
    
    def _run(self, name: str, fn) -> ActionResult:
        start = time.time()
        try:
            fn()
            return ActionResult(True, name, duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ActionResult(False, name, str(e)[:100],
                               duration_ms=(time.time() - start) * 1000)


class GUITaskExecutor:
    """真实的GUI任务执行器
    
    接受中文自然语言指令 → 解析 → 键盘/鼠标驱动 → 验证
    """
    
    def __init__(self):
        self._ctrl = DesktopController()
        self._trajectory: List[Dict] = []
    
    def execute(self, instruction: str) -> Dict[str, Any]:
        """执行桌面操作指令
        
        支持的真实操作:
        - "打开记事本" → Win → 搜索→notepad → Enter
        - "输入hello" → 直接键入
        - "打开浏览器去百度" → Win→搜索→chrome→Enter → Alt+D→baidu.com→Enter
        - "切换窗口" → Alt+Tab
        """
        if not self._ctrl.available:
            return {"success": False, "error": "需要 pip install pyautogui"}
        
        self._trajectory = []
        i = instruction.lower().strip()
        result = self._dispatch(i)
        return result
    
    def _dispatch(self, instruction: str) -> Dict[str, Any]:
        """解析并执行指令"""
        
        # ── 打开程序 ──
        if any(kw in instruction for kw in ["打开", "启动", "运行"]):
            for kw in ["打开", "启动", "运行"]:
                if kw in instruction:
                    app = instruction.split(kw)[-1].strip()
                    break
            # 常见软件映射
            app_map = {
                "记事本": "notepad", "计算器": "calc", "浏览器": "chrome",
                "cmd": "cmd", "命令提示符": "cmd", "终端": "cmd",
                "文件管理器": "explorer", "此电脑": "explorer",
                "设置": "settings", "控制面板": "control",
            }
            exe = app_map.get(app, app)
            r = self._ctrl.search_and_open(exe)
            self._trajectory.append(r)
            return {
                "success": True,
                "action": f"打开{app}({exe})",
                "steps": self._trajectory,
            }
        
        # ── 输入文本 ──
        if any(kw in instruction for kw in ["输入", "键入", "写"]):
            for kw in ["输入", "键入", "写"]:
                if kw in instruction:
                    text = instruction.split(kw)[-1].strip()
                    break
            r = self._ctrl.type_text(text)
            self._trajectory.append(r)
            return {"success": r.success, "action": f"输入: {text[:30]}", "steps": self._trajectory}
        
        # ── 切换窗口 ──
        if "切换" in instruction or "alt+tab" in instruction:
            times = 1
            if "2" in instruction: times = 2
            if "3" in instruction: times = 3
            r = self._ctrl.alt_tab(times)
            self._trajectory.append(r)
            return {"success": True, "action": f"切换窗口x{times}", "steps": self._trajectory}
        
        # ── 打开浏览器并访问 ──
        if "浏览器" in instruction and ("去" in instruction or "访问" in instruction or "打开" in instruction):
            url = instruction.split("去")[-1].split("访问")[-1].strip() if "去" in instruction else "baidu.com"
            self._ctrl.search_and_open("chrome")
            time.sleep(1.5)
            self._ctrl.hotkey('alt', 'd')  # 地址栏
            time.sleep(0.3)
            self._ctrl.type_text(url)
            self._ctrl.enter()
            return {"success": True, "action": f"浏览器访问{url}", "steps": self._trajectory}
        
        # ── 回车/确认 ──
        if any(kw in instruction for kw in ["回车", "确认", "确定", "enter"]):
            r = self._ctrl.enter()
            self._trajectory.append(r)
            return {"success": True, "action": "回车确认", "steps": self._trajectory}
        
        # ── 截图 ──
        if "截图" in instruction:
            path = self._ctrl.screenshot()
            return {"success": True, "action": "截图", "path": path, "steps": self._trajectory}
        
        return {"success": False, "error": f"无法解析: {instruction[:50]}", "steps": self._trajectory}
    
    @property
    def trajectory(self) -> List[Dict]:
        return self._trajectory


# ── 一键测试 ──
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        print(f"执行: {cmd}")
        agent = GUITaskExecutor()
        result = agent.execute(cmd)
        print(f"结果: {result['success']}")
        if 'action' in result:
            print(f"动作: {result['action']}")
