from typing import Dict, Any, Optional
from loguru import logger
import subprocess
import os
import tempfile

from ..types import ExecutionProfile


class Sandbox:
    def __init__(self, work_dir: str = "./sandbox"):
        self._work_dir = work_dir
        self._profiles = {
            ExecutionProfile.READ_ONLY: {"read": True, "write": False, "execute": False, "network": False},
            ExecutionProfile.SANDBOX: {"read": True, "write": True, "execute": True, "network": False},
            ExecutionProfile.ISOLATED: {"read": True, "write": True, "execute": True, "network": False},
            ExecutionProfile.FULL: {"read": True, "write": True, "execute": True, "network": True},
            ExecutionProfile.DANGEROUS: {"read": True, "write": True, "execute": True, "network": True},
        }
        os.makedirs(work_dir, exist_ok=True)
        logger.info("Sandbox initialized")

    def execute(self, code: str, profile: ExecutionProfile = ExecutionProfile.SANDBOX) -> Dict[str, Any]:
        config = self._profiles.get(profile)
        if not config:
            return {"success": False, "error": f"Unknown profile: {profile}"}

        logger.info(f"Executing code in sandbox with profile: {profile}")

        if not config["execute"]:
            return {"success": False, "error": "Execution not allowed in this profile"}

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=self._work_dir) as f:
                f.write(code)
                temp_file = f.name

            result = subprocess.run(
                ["python", temp_file],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self._work_dir,
            )

            os.unlink(temp_file)

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_file(self, path: str, profile: ExecutionProfile = ExecutionProfile.SANDBOX) -> Dict[str, Any]:
        config = self._profiles.get(profile)
        if not config or not config["read"]:
            return {"success": False, "error": "Read not allowed in this profile"}

        full_path = os.path.join(self._work_dir, path)

        if not full_path.startswith(self._work_dir):
            return {"success": False, "error": "Path traversal detected"}

        try:
            with open(full_path, "r") as f:
                content = f.read()

            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, path: str, content: str, profile: ExecutionProfile = ExecutionProfile.SANDBOX) -> Dict[str, Any]:
        config = self._profiles.get(profile)
        if not config or not config["write"]:
            return {"success": False, "error": "Write not allowed in this profile"}

        full_path = os.path.join(self._work_dir, path)

        if not full_path.startswith(self._work_dir):
            return {"success": False, "error": "Path traversal detected"}

        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_files(self, profile: ExecutionProfile = ExecutionProfile.SANDBOX) -> Dict[str, Any]:
        config = self._profiles.get(profile)
        if not config or not config["read"]:
            return {"success": False, "error": "Read not allowed in this profile"}

        try:
            files = []
            for root, dirs, filenames in os.walk(self._work_dir):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, self._work_dir)
                    files.append(rel_path)

            return {"success": True, "files": files}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def can_access_network(self, profile: ExecutionProfile) -> bool:
        config = self._profiles.get(profile)
        return config.get("network", False) if config else False
