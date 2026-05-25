"""AutoUpdate — 自动更新检查 (接入层)

启动时检查 GitHub 版本, 有新版本提示用户。
"""

import json
import os
import time
import httpx
from pathlib import Path

CURRENT_VERSION = "1.0.0"
UPDATE_CHECK_FILE = Path.home() / ".xiaohei" / ".update_check"
OWNER = "ff4554825-sys"
REPO = "xiaohei"


def check_update() -> dict:
    """检查 GitHub Release 是否有新版本"""
    now = time.time()
    
    # 缓存检查 (24小时内不重复请求)
    if UPDATE_CHECK_FILE.exists():
        try:
            data = json.loads(UPDATE_CHECK_FILE.read_text())
            if now - data.get("checked_at", 0) < 86400:
                return data
        except Exception:
            pass
    
    result = {
        "current": CURRENT_VERSION,
        "latest": CURRENT_VERSION,
        "has_update": False,
        "release_url": f"https://github.com/{OWNER}/{REPO}/releases",
        "checked_at": now,
    }
    
    try:
        resp = httpx.get(
            f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest",
            timeout=5,
            headers={"User-Agent": "xiaohei/1.0"}
        )
        if resp.status_code == 200:
            data = resp.json()
            latest = data.get("tag_name", "").lstrip("v")
            result["latest"] = latest
            result["release_url"] = data.get("html_url", result["release_url"])
            result["has_update"] = latest > CURRENT_VERSION
    except Exception:
        pass
    
    UPDATE_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
    UPDATE_CHECK_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    
    return result


def print_update_notice():
    """打印版本更新提示"""
    info = check_update()
    if info["has_update"]:
        print(f"\n⬆️  新版本可用: v{info['current']} → v{info['latest']}")
        print(f"   下载: {info['release_url']}\n")
    else:
        print(f"  ✔ 当前版本 v{info['current']} (已是最新)")


if __name__ == "__main__":
    print_update_notice()
