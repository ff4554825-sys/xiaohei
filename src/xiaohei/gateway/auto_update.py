"""AutoUpdate — 自动更新系统 (接入层)

全流程: 检查 → 下载 → 验证 → 安装
"""

import json
import os
import sys
import time
import httpx
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from loguru import logger

CURRENT_VERSION = "1.0.0"
UPDATE_CHECK_FILE = Path.home() / ".xiaohei" / ".update_check"
OWNER = "ff4554825-sys"
REPO = "xiaohei"


class UpdateInfo:
    """版本更新信息"""
    def __init__(self, has_update=False, latest="", current="",
                 download_url="", release_url="", release_notes=""):
        self.has_update = has_update
        self.latest = latest
        self.current = current
        self.download_url = download_url
        self.release_url = release_url
        self.release_notes = release_notes
    
    @property
    def needs_update(self) -> bool:
        return self.has_update
    
    def __str__(self) -> str:
        if self.has_update:
            return f"⬆️  v{self.current} → v{self.latest}"
        return f"✔  v{self.current} (已是最新)"


def check_update(force: bool = False) -> UpdateInfo:
    """检查 GitHub Release 更新"""
    now = time.time()
    
    # 缓存检查(24h内不重复请求)
    if not force and UPDATE_CHECK_FILE.exists():
        try:
            data = json.loads(UPDATE_CHECK_FILE.read_text())
            if now - data.get("checked_at", 0) < 86400:
                return UpdateInfo(
                    has_update=data.get("has_update", False),
                    latest=data.get("latest", CURRENT_VERSION),
                    current=CURRENT_VERSION,
                    download_url=data.get("download_url", ""),
                    release_url=data.get("release_url", ""),
                )
        except Exception:
            pass
    
    info = UpdateInfo(current=CURRENT_VERSION)
    
    try:
        resp = httpx.get(
            f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest",
            timeout=10,
            headers={"User-Agent": "xiaohei/1.0", "Accept": "application/json"}
        )
        if resp.status_code == 200:
            data = resp.json()
            tag = data.get("tag_name", "").lstrip("v")
            info.latest = tag
            info.release_url = data.get("html_url", "")
            info.release_notes = data.get("body", "")[:500]
            
            # 找到下载链接
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".whl") or name.endswith(".tar.gz"):
                    info.download_url = asset.get("browser_download_url", "")
                    break
            
            # 版本比较
            info.has_update = self._version_compare(tag, CURRENT_VERSION) > 0
    
    except Exception as e:
        logger.warning(f"[update] 检查更新失败: {e}")
    
    # 缓存
    UPDATE_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
    UPDATE_CHECK_FILE.write_text(json.dumps({
        "checked_at": now,
        "has_update": info.has_update,
        "latest": info.latest,
        "download_url": info.download_url,
        "release_url": info.release_url,
    }, ensure_ascii=False))
    
    return info


def _version_compare(v1: str, v2: str) -> int:
    """版本比较: v1>v2返回1, v1<v2返回-1, 相等返回0"""
    parts1 = [int(x) for x in v1.split(".")]
    parts2 = [int(x) for x in v2.split(".")]
    for i in range(max(len(parts1), len(parts2))):
        p1 = parts1[i] if i < len(parts1) else 0
        p2 = parts2[i] if i < len(parts2) else 0
        if p1 > p2:
            return 1
        if p1 < p2:
            return -1
    return 0


def download_update(url: str) -> Optional[Path]:
    """下载更新包"""
    if not url:
        logger.error("[update] 无下载链接")
        return None
    
    tmp_dir = Path(tempfile.mkdtemp(prefix="xiaohei_update_"))
    dest = tmp_dir / "update.zip"
    
    try:
        logger.info(f"[update] 开始下载: {url}")
        with httpx.stream("GET", url, timeout=60) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
        logger.info(f"[update] 下载完成: {downloaded / 1024 / 1024:.1f}MB")
        return dest
    except Exception as e:
        logger.error(f"[update] 下载失败: {e}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None


def install_update(package_path: Path) -> bool:
    """安装更新包(pip install)"""
    try:
        logger.info(f"[update] 开始安装: {package_path}")
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", str(package_path)],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0:
            logger.info("[update] 安装成功!")
            return True
        else:
            logger.error(f"[update] 安装失败: {r.stderr[:200]}")
            return False
    except Exception as e:
        logger.error(f"[update] 安装异常: {e}")
        return False


def do_full_update() -> bool:
    """执行完整更新流程: 检查 → 下载 → 安装"""
    info = check_update(force=True)
    
    if not info.has_update:
        print(str(info))
        return False
    
    print(str(info))
    print(f"  发行说明: {info.release_url}")
    
    if not info.download_url:
        print("  ❌ 无下载链接, 请手动更新")
        return False
    
    package = download_update(info.download_url)
    if not package:
        return False
    
    success = install_update(package)
    
    # 清理
    try:
        shutil.rmtree(package.parent, ignore_errors=True)
    except Exception:
        pass
    
    return success


def print_update_notice():
    """启动时打印版本提示"""
    info = check_update()
    if info.has_update:
        print(f"\n⬆️  新版本可用: v{info.current} → v{info.latest}")
        print(f"   运行 'python start.py --update' 升级\n")
    else:
        print(f"  ✔ v{info.current}")


if __name__ == "__main__":
    import sys
    if "--update" in sys.argv:
        do_full_update()
    else:
        print_update_notice()
