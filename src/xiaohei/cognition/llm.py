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


def _resolve_api_key() -> str:
    """从多个来源获取 API Key"""
    # 1. 环境变量
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    # 2. 配置文件
    config_path = Path.home() / ".xiaohei" / "config.yaml"
    if config_path.exists():
        try:
            import yaml
            cfg = yaml.safe_load(config_path.read_text())
            key = cfg.get("providers", {}).get("deepseek", {}).get("api_key", "")
            key = key or cfg.get("providers", {}).get("openai", {}).get("api_key", "")
            if key:
                return key
        except Exception:
            pass
    # 3. 旧版 hermes auth
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


_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = _resolve_api_key()
        if not api_key:
            logger.warning("[llm] 未找到 API Key, LLM 调用将返回模拟结果")
            return None
        base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
        if _HAS_OPENAI:
            _client = OpenAI(api_key=api_key, base_url=f"{base_url}/v1")
        else:
            logger.warning("[llm] openai 库未安装, 使用 httpx 直接调用")
    return _client


def call_llm(system: str, user: str, model: str = "deepseek-chat",
             temperature: float = 0.7, max_tokens: int = 2048) -> str:
    """调用 LLM, 返回文本响应"""
    client = _get_client()
    
    if client is None:
        logger.warning("[llm] LLM 不可用, 返回模拟响应")
        return _fallback_response(system, user)
    
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
        logger.debug(f"[llm] 响应: {text[:80]}...")
        return text or ""
    except Exception as e:
        logger.error(f"[llm] 调用失败: {e}")
        return _fallback_response(system, user)


def call_llm_json(system: str, user: str, model: str = "deepseek-chat",
                  temperature: float = 0.3) -> dict:
    """调用 LLM 并解析 JSON 响应"""
    text = call_llm(system, user + "\n\n请只返回JSON, 不要包含其他文字。", 
                    model, temperature)
    # 尝试提取 JSON
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
