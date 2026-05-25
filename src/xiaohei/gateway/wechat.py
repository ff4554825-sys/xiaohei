"""WeChat 平台适配器 (多平台接入)

通过 OpenClaw/ClawBot 中转, 接收微信消息 → 小黑 API → 回复回微信

使用方式:
  1. 确保 OpenClaw Gateway 在运行(端口 18789)
  2. 在 OpenClaw 中配置 webhook 指向本服务的 /webhook/wechat
  3. 微信消息通过 ClawBot → Gateway → webhook → 小黑
"""

import json
import httpx
import hmac
import hashlib
from typing import Optional
from loguru import logger
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/webhook", tags=["wechat"])

_OPENCLAW_URL = "http://127.0.0.1:18789"
_XIAOHEI_URL = "http://127.0.0.1:3721"


@router.post("/wechat")
async def wechat_webhook(request: Request):
    """接收来自 OpenClaw Gateway 的微信消息转发"""
    try:
        body = await request.json()
        logger.info(f"[wechat] 收到消息: {body.get('content', '')[:60]}")
        
        # 提取消息内容
        content = body.get("content", "")
        sender = body.get("from", "")
        
        if not content:
            return {"status": "ignored"}
        
        # 调用小黑 API
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_XIAOHEI_URL}/api/chat",
                json={"message": content, "session_id": f"wechat_{sender}"},
                timeout=30
            )
            result = resp.json()
        
        return {"status": "ok", "reply": result.get("message", "")}
    
    except Exception as e:
        logger.error(f"[wechat] 处理失败: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/wechat/status")
def wechat_status():
    """检查 WeChat 接入状态"""
    return {
        "platform": "wechat",
        "gateway": _OPENCLAW_URL,
        "connected": False,  # 由 OpenClaw 管理
        "note": "通过 OpenClaw Gateway + ClawBot 转发"
    }
