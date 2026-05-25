"""Config — 配置管理器 (接入层)

从旧 agent-arch/config.py 迁移
"""

import os
import yaml
from pathlib import Path

CONFIG_PATH = Path.home() / ".xiaohei" / "config.yaml"
ENV_PATH = Path(__file__).parent / ".env"


def _load_yaml(path: Path) -> dict:
    if path.exists():
        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    return {}


def _load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env


_defaults = {
    "agent": {"name": "小黑", "mode": "dual"},
    "api": {"host": "0.0.0.0", "port": 3721},
    "runtime": {"mode": "xiaohei", "timeout_s": 300},
    "memory": {"path": str(Path.home() / ".xiaohei" / "memory")},
    "gateway": {
        "platforms": ["cli", "web"],
        "hook_port": 3722,
    },
}


class Config:
    def __init__(self):
        self._data = dict(_defaults)
        self._merge(_load_yaml(CONFIG_PATH))
        self._merge(_load_env(ENV_PATH))
        self._merge(os.environ)  # env vars override everything

    def _merge(self, src: dict):
        for k, v in src.items():
            if k.isupper():
                # 仅处理已知的小黑配置环境变量
                known_keys = {"DEEPSEEK_API_KEY", "XIAOHEI_MODE", "XIAOHEI_PORT",
                             "PROVIDER_BASE_URL", "PROXY_ENABLED", "PROXY_SOCKS5"}
                if k not in known_keys:
                    continue
                key = k.lower().replace("_", ".")
                self._set_nested(key, v)
            elif isinstance(v, str) and not isinstance(v, (int, float)):
                self._data[k] = v
            else:
                self._data[k] = v

    def _set_nested(self, key: str, value):
        parts = key.split(".")
        d = self._data
        for p in parts[:-1]:
            d = d.setdefault(p, {})
        d[parts[-1]] = value

    def get(self, *keys, default=None):
        d = self._data
        for k in keys:
            if isinstance(d, dict):
                d = d.get(k, {})
            else:
                return default
        return d if d != {} else default

    @property
    def api_key(self) -> str:
        return self.get("provider", "deepseek_api_key") or os.environ.get("DEEPSEEK_API_KEY", "")

    @property
    def port(self) -> int:
        return int(self.get("api", "port", default=3721))

    @property
    def agent_name(self) -> str:
        return self.get("agent", "name", default="小黑")

    @property
    def runtime_mode(self) -> str:
        return self.get("runtime", "mode", default="xiaohei")

    def is_first_launch(self) -> bool:
        return not self.api_key


config = Config()
