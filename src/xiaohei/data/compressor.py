from typing import List, Dict, List, Any, Optional
from loguru import logger
from datetime import datetime

from ..types import CompressedContext


class Compressor:
    def __init__(self):
        logger.info("Compressor initialized")

    def compress(self, text: str, max_length: int = 500) -> CompressedContext:
        original_length = len(text)

        if original_length <= max_length:
            return CompressedContext(
                original_length=original_length,
                compressed_length=original_length,
                summary=text,
                key_points=[text],
            )

        sentences = text.split("。")
        if len(sentences) == 0:
            sentences = text.split(".")

        key_points = []
        compressed_text = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(compressed_text) + len(sentence) + 1 <= max_length:
                compressed_text += sentence + "。"
                if len(sentence) > 10:
                    key_points.append(sentence[:30] + "...")

        compressed_length = len(compressed_text)

        logger.debug(f"Compressed text: {original_length} -> {compressed_length}")

        return CompressedContext(
            original_length=original_length,
            compressed_length=compressed_length,
            summary=compressed_text,
            key_points=key_points[:5],
        )

    def compress_dialogue(self, dialogue: List[Dict[str, str]], max_messages: int = 10) -> CompressedContext:
        if len(dialogue) <= max_messages:
            full_text = "\n".join([f"{m['role']}: {m['content']}" for m in dialogue])
            return CompressedContext(
                original_length=len(full_text),
                compressed_length=len(full_text),
                summary=full_text,
                key_points=[m["content"][:30] + "..." for m in dialogue[-3:]],
            )

        recent_dialogue = dialogue[-max_messages:]
        compressed_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent_dialogue])

        key_points = []
        for msg in recent_dialogue[-3:]:
            content = msg["content"]
            key_points.append(f"{msg['role']}: {content[:30]}...")

        return CompressedContext(
            original_length=sum(len(m["content"]) for m in dialogue),
            compressed_length=len(compressed_text),
            summary=compressed_text,
            key_points=key_points,
        )

    def get_compression_ratio(self, original: str, compressed: str) -> float:
        if not original:
            return 0.0
        return len(compressed) / len(original)
