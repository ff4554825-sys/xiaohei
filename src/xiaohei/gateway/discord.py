"""Discord 平台适配器 (多平台接入)

通过 Webhook 接收 Discord 消息, 回复到指定频道。

使用方式:
  1. 在 Discord Developer Portal 创建应用
  2. 开启 MESSAGE CONTENT INTENT
  3. 设置 INTERACTIONS ENDPOINT URL 指向本服务的 /webhook/discord
"""

import json
import httpx
from typing import Optional
from loguru import logger
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/webhook", tags=["discord"])

_XIAOHEI_URL = "http://127.0.0.1:3721"
_DISCORD_API = "https://discord.com/api/v10"


@router.post("/discord")
async def discord_webhook(request: Request):
    """接收 Discord Interaction (Slash Command 或消息)"""
    try:
        body = await request.json()
        
        # Discord 的 Ping 验证
        if body.get("type") == 1:
            return {"type": 1}  # Pong
        
        # 提取消息内容
        data = body.get("data", {})
        content = data.get("content", "") or data.get("name", "")
        channel_id = body.get("channel_id", "")
        user = body.get("member", {}).get("user", {}).get("username", "unknown")
        
        if not content:
            return {"type": 4, "data": {"content": "请发送消息"}}
        
        # 调用小黑 API
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_XIAOHEI_URL}/api/chat",
                json={"message": f"[Discord]({user}) {content}", "session_id": f"discord_{channel_id}"},
                timeout=30
            )
            result = resp.json()
        
        return {
            "type": 4,
            "data": {
                "content": (result.get("message", "") or "处理完成")[:2000]
            }
        }
    
    except Exception as e:
        logger.error(f"[discord] 处理失败: {e}")
        return {"type": 4, "data": {"content": f"❌ 处理失败: {str(e)[:100]}"}}


@router.get("/discord/status")
def discord_status():
    return {"platform": "discord", "ready": True}
