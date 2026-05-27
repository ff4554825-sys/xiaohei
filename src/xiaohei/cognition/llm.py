"""LLM — 真实的 LLM 调用器 (认知层)

通过 DeepSeek API 调用, 供所有认知模块使用。
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


def _resolve_api_key(provider: str = "deepseek") -> str:
    """从多个来源获取 API Key，支持指定 provider"""
    env_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "claude": "CLAUDE_API_KEY",
        "mimo": "MIMO_API_KEY",
    }
    
    # 1. 环境变量
    env_name = env_map.get(provider, f"{provider.upper()}_API_KEY")
    key = os.environ.get(env_name)
    if key and key not in ("", "your-api-key-here"):
        return key
    
    # 2. 项目 .env 文件
    for env_path in [
        Path(__file__).parent.parent.parent.parent / ".env",
        Path.cwd() / ".env",
    ]:
        if env_path.exists():
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(f"{env_name}="):
                            val = line.split("=", 1)[1].strip().strip("\"'")
                            if val and val != "your-api-key-here":
                                return val
            except Exception:
                pass
    
    # 3. 配置文件
    config_path = Path.home() / ".xiaohei" / "config.yaml"
    if config_path.exists():
        try:
            import yaml
            cfg = yaml.safe_load(config_path.read_text())
            key = cfg.get("providers", {}).get(provider, {}).get("api_key", "")
            if key and key not in ("", "your-api-key-here"):
                return key
        except Exception:
            pass
    
    # 4. 旧版 hermes auth
    auth_path = Path.home() / "AppData" / "Local" / "hermes" / "auth.json"
    if auth_path.exists():
        try:
            auth = json.loads(auth_path.read_text())
            for cred in auth.get("credential_pool", {}).get("deepseek", []):
                key = cred.get("access_token", "")
                if key:
                    return key
        except Exception:
            pass
    return ""


PROVIDER_CONFIG = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "mimo": {
        "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
        "model": "mimo-v2.5-pro",
    },
    "claude": {
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-3-sonnet-20240229",
    },
}

_clients = {}


def _get_client(provider: str = "deepseek"):
    global _clients
    if provider not in _clients:
        api_key = _resolve_api_key(provider)
        if not api_key:
            logger.warning(f"[llm] 未找到 {provider} API Key, 将返回模拟结果")
            return None
        
        cfg = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["deepseek"])
        base_url = os.environ.get(f"{provider.upper()}_BASE_URL", cfg["base_url"])
        
        if _HAS_OPENAI:
            _clients[provider] = OpenAI(api_key=api_key, base_url=str(base_url))
        else:
            logger.warning("[llm] openai 库未安装, 使用 httpx 直接调用")
    return _clients.get(provider)


def call_llm(system: str, user: str, model: str = None,
             provider: str = "deepseek", temperature: float = 0.7,
             max_tokens: int = 2048) -> str:
    """调用 LLM, 返回文本响应。可指定 provider: deepseek/openai/mimo/claude"""
    client = _get_client(provider)
    
    if client is None:
        logger.warning(f"[llm] {provider} 不可用, 返回模拟响应")
        return _fallback_response(system, user)
    
    # 使用 provider 默认模型
    if model is None:
        model = PROVIDER_CONFIG.get(provider, {}).get("model", "deepseek-chat")
    
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = resp.choices[0].message.content
        logger.debug(f"[llm:{provider}] 响应: {text[:80]}...")
        return text or ""
    except Exception as e:
        logger.error(f"[llm:{provider}] 调用失败: {e}")
        return _fallback_response(system, user)


def call_llm_json(system: str, user: str, model: str = None,
                  provider: str = "deepseek", temperature: float = 0.3) -> dict:
    """调用 LLM 并解析 JSON 响应"""
    text = call_llm(system, user + "\n\n请只返回JSON, 不要包含其他文字。", 
                    model, provider, temperature)
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"[llm] JSON 解析失败: {text[:100]}")
        return {"error": "parse_failed", "raw": text[:100]}


def _fallback_response(system: str, user: str) -> str:
    """LLM 不可用时的模拟响应(仅开发调试用)"""
    # 尝试从 system prompt 和 user 输入中提取有意义的响应
    user_lower = user.lower()
    
    if "plan" in system.lower() or "规划" in system:
        return json.dumps({
            "steps": [
                {"action": "分析需求", "tool": "llm_chat"},
                {"action": "执行方案", "tool": "python_exec"},
                {"action": "验证结果", "tool": "memory_search"},
            ],
            "reasoning": "基于任务需求的标准三步规划",
        })
    
    if "critic" in system.lower() or "批评" in system or "评估" in system:
        if "hello" in user_lower or "hi" in user_lower:
            score = 8
        else:
            score = 5
        return json.dumps({
            "score": score,
            "passed": score >= 6,
            "issues": [] if score >= 6 else ["结果不够完整"],
            "suggestion": "继续完善",
        })
    
    if "debate" in system.lower() or "辩论" in system:
        role = "执行者"
        if "planner" in system.lower():
            role = "规划者"
        elif "critic" in system.lower():
            role = "评论者"
        return json.dumps({
            "opinion": f"作为{role}: 建议分步骤完成该任务",
            "confidence": 0.7,
        })
    
    return f"收到请求: {user[:50]}"
