from typing import List, Dict, List, Any, Optional
from loguru import logger
from datetime import datetime

from ..types import Event, EventType


class ConversationCompression:
    def __init__(self, compressor=None, event_bus=None):
        self._compressor = compressor
        self._event_bus = event_bus
        logger.info("ConversationCompression initialized")

    def manage_long_conversation(self, messages: List[Dict[str, str]], max_tokens: int = 4096) -> List[Dict[str, str]]:
        total_tokens = sum(self._count_tokens(m["content"]) for m in messages)

        if total_tokens <= max_tokens:
            return messages

        compressed = self._compress_conversation(messages, max_tokens)

        if self._event_bus:
            self._event_bus.publish(
                Event(
                    type=EventType.LOG,
                    payload={
                        "message": f"Compressed conversation: {len(messages)} -> {len(compressed)} messages",
                        "tokens": total_tokens,
                    },
                    source="conversation_compression",
                )
            )

        logger.info(f"Compressed conversation from {len(messages)} to {len(compressed)} messages")
        return compressed

    def _count_tokens(self, text: str) -> int:
        return len(text) // 4

    def _compress_conversation(self, messages: List[Dict[str, str]], max_tokens: int) -> List[Dict[str, str]]:
        if not self._compressor:
            return messages[-10:]

        recent_messages = messages[-5:]
        earlier_messages = messages[:-5]

        if not earlier_messages:
            return messages

        compressed_summary = self._compressor.compress_dialogue(earlier_messages)

        compressed_messages = [
            {
                "role": "system",
                "content": f"对话摘要:\n{compressed_summary.summary}",
            }
        ] + recent_messages

        return compressed_messages

    def summarize_turn(self, user_message: str, assistant_response: str) -> str:
        if not self._compressor:
            return f"User: {user_message}\nAssistant: {assistant_response}"

        combined = f"User: {user_message}\nAssistant: {assistant_response}"
        compressed = self._compressor.compress(combined)
        return compressed.summary
