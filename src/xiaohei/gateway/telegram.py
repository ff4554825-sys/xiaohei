"""Telegram 平台适配器 (多平台接入)

通过 Webhook 接收 Telegram 消息, 回复到对应 chat。

使用方式:
  1. 在 @BotFather 创建 bot, 获取 token
  2. 设置 Webhook: 
     curl https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your.domain/webhook/telegram
"""

import json
import httpx
from typing import Optional
from loguru import logger
from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhook", tags=["telegram"])

_TG_API = "https://api.telegram.org/bot"
_XIAOHEI_URL = "http://127.0.0.1:3721"
_BOT_TOKEN = ""  # 运行时设置


@router.post("/telegram")
async def telegram_webhook(request: Request):
    """接收 Telegram Update"""
    try:
        body = await request.json()
        
        # 提取消息
        message = body.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id", "")
        user = message.get("from", {}).get("first_name", "unknown")
        
        if not text or text.startswith("/"):
            return {"ok": True}
        
        logger.info(f"[telegram] 来自 {user}: {text[:60]}")
        
        # 调用小黑 API
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_XIAOHEI_URL}/api/chat",
                json={"message": f"[Telegram]({user}) {text}", "session_id": f"tg_{chat_id}"},
                timeout=30
            )
            result = resp.json()
        
        reply = (result.get("message", "") or "处理完成")[:2000]
        
        # 回复到 Telegram
        if _BOT_TOKEN and chat_id:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{_TG_API}{_BOT_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": reply}
                )
        
        return {"ok": True}
    
    except Exception as e:
        logger.error(f"[telegram] 处理失败: {e}")
        return {"ok": False, "error": str(e)}


def set_bot_token(token: str):
    global _BOT_TOKEN
    _BOT_TOKEN = token
    logger.info(f"[telegram] Bot token 已设置")


@router.get("/telegram/status")
def telegram_status():
    return {"platform": "telegram", "has_token": bool(_BOT_TOKEN)}
