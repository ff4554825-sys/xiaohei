"""Daemon — 后台守护脚本 (接入层)

支持:
- Windows: 系统托盘 (pystray)
- Unix: 后台进程
"""

import os
import sys
import time
import threading
from pathlib import Path

new_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(new_root))
sys.path.insert(0, str(new_root / "src"))

# 尝试导入托盘 (Windows 需要 pystray + PIL)
try:
    import pystray
    from PIL import Image
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


class XiaoHeiDaemon:
    """守护进程"""
    
    def __init__(self):
        self._running = False
        self._server_thread = None
        self._tray_icon = None
    
    def start(self, mode: str = "web", host: str = "0.0.0.0", port: int = 3721):
        """启动小黑服务"""
        self._running = True
        
        # 启动 Web 服务
        if mode in ("web", "both"):
            self._server_thread = threading.Thread(
                target=self._run_web,
                args=(host, port),
                daemon=True
            )
            self._server_thread.start()
            print(f"  🚀 小黑已启动: http://{host}:{port}")
        
        # 启动系统托盘 (Windows)
        if HAS_TRAY and os.name == 'nt':
            self._start_tray()
        else:
            # 没有托盘就等待 Ctrl+C
            print("  按 Ctrl+C 停止")
            try:
                while self._running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
    
    def _run_web(self, host: str, port: int):
        from src.xiaohei.gateway.web_server import WebServer
        server = WebServer()
        server.run(host=host, port=port)
    
    def _start_tray(self):
        """启动系统托盘"""
        # 创建一个简单的图标 (16x16 蓝色方块)
        img = Image.new('RGB', (16, 16), (30, 111, 235))
        
        menu = (
            pystray.MenuItem("打开界面", lambda: os.system(f"start http://localhost:3721")),
            pystray.MenuItem("重新启动", self._restart),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self.stop),
        )
        
        self._tray_icon = pystray.Icon("xiaohei", img, "小黑 Agent OS", menu)
        self._tray_icon.run()
    
    def _restart(self):
        self.stop()
        time.sleep(1)
        self.start()
    
    def stop(self):
        self._running = False
        if self._tray_icon:
            self._tray_icon.stop()
        print("  👋 小黑已停止")
        os._exit(0)


def run_daemon(mode="web", host="0.0.0.0", port=3721):
    daemon = XiaoHeiDaemon()
    daemon.start(mode, host, port)


if __name__ == "__main__":
    run_daemon()
