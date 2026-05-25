"""Checkpoint — 状态检查点 + 持久化恢复 (数据平面)

定期保存运行时状态, 崩溃后恢复。
"""

import json
import time
import threading
import os
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

CHECKPOINT_DIR = Path.home() / ".xiaohei" / "checkpoints"
MAX_CHECKPOINTS = 10
AUTO_SAVE_INTERVAL = 300  # 5分钟


class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self):
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        self._timer: Optional[threading.Timer] = None
        self._running = False
        self._state: Dict[str, Any] = {
            "sessions": {},
            "memories": {},
            "config": {},
            "started_at": time.time(),
            "last_checkpoint": 0,
        }
    
    def update(self, key: str, value: Any):
        """更新运行时状态"""
        self._state[key] = value
    
    def save(self, name: str = "latest") -> Path:
        """保存检查点"""
        self._state["last_checkpoint"] = time.time()
        path = CHECKPOINT_DIR / f"{name}.json"
        
        # 写入临时文件再重命名(防止写入损坏)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2, default=str)
        tmp.rename(path)
        
        # 清理旧检查点
        self._cleanup()
        
        return path
    
    def load(self, name: str = "latest") -> Optional[Dict[str, Any]]:
        """加载检查点"""
        path = CHECKPOINT_DIR / f"{name}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._state = json.load(f)
            logger.info(f"[checkpoint] 已恢复状态: {name}")
            return self._state
        except Exception as e:
            logger.error(f"[checkpoint] 恢复失败: {e}")
            return None
    
    def auto_save_loop(self):
        """自动保存循环(后台线程)"""
        self._running = True
        while self._running:
            time.sleep(AUTO_SAVE_INTERVAL)
            try:
                self.save("auto")
                logger.debug("[checkpoint] 自动保存完成")
            except Exception as e:
                logger.error(f"[checkpoint] 自动保存失败: {e}")
    
    def start_auto_save(self):
        """启动自动保存"""
        thread = threading.Thread(target=self.auto_save_loop, daemon=True)
        thread.start()
    
    def stop_auto_save(self):
        self._running = False
    
    def list_checkpoints(self) -> list:
        """列出所有检查点"""
        checkpoints = []
        for f in sorted(CHECKPOINT_DIR.glob("*.json")):
            checkpoints.append({
                "name": f.stem,
                "size": f.stat().st_size,
                "mtime": f.stat().st_mtime,
            })
        return checkpoints
    
    def _cleanup(self):
        """清理超出最大数量的旧检查点"""
        files = sorted(CHECKPOINT_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime)
        while len(files) > MAX_CHECKPOINTS:
            files[0].unlink()
            files.pop(0)
    
    @property
    def stats(self) -> dict:
        return {
            "checkpoints": len(list(CHECKPOINT_DIR.glob("*.json"))),
            "auto_save_interval": AUTO_SAVE_INTERVAL,
            "uptime": time.time() - self._state.get("started_at", time.time()),
        }
