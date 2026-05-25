from typing import List, Dict, List, Any, Optional
from uuid import UUID
from loguru import logger
from datetime import datetime
import sqlite3
import os

from ..types import MemoryItem, MemoryLevel


class MemoryStore:
    def __init__(self, db_path: str = "./data/memory.db"):
        self._db_path = db_path
        self._init_db()
        logger.info(f"MemoryStore initialized with db: {db_path}")

    def _init_db(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_items (
                    id TEXT PRIMARY KEY,
                    level TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    embedding BLOB,
                    created_at TIMESTAMP NOT NULL,
                    accessed_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_key ON memory_items(key)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_level ON memory_items(level)
            """)

            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(key, value)
            """)

            conn.commit()

    def write(self, item: MemoryItem) -> None:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO memory_items (
                    id, level, key, value, embedding, created_at, accessed_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(item.id),
                item.level.value,
                item.key,
                str(item.value),
                bytes(item.embedding) if item.embedding else None,
                item.created_at.isoformat(),
                item.accessed_at.isoformat(),
                item.expires_at.isoformat() if item.expires_at else None,
            ))

            cursor.execute("""
                INSERT OR REPLACE INTO memory_fts (rowid, key, value)
                VALUES ((SELECT rowid FROM memory_items WHERE id = ?), ?, ?)
            """, (str(item.id), item.key, str(item.value)))

            conn.commit()

        logger.debug(f"Memory item written: {item.key}")

    def read(self, key: str) -> Optional[MemoryItem]:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, level, key, value, embedding, created_at, accessed_at, expires_at
                FROM memory_items WHERE key = ?
            """, (key,))

            row = cursor.fetchone()
            if row:
                return MemoryItem(
                    id=UUID(row[0]),
                    level=MemoryLevel(row[1]),
                    key=row[2],
                    value=row[3],
                    embedding=list(bytes(row[4])) if row[4] else None,
                    created_at=datetime.fromisoformat(row[5]),
                    accessed_at=datetime.fromisoformat(row[6]),
                    expires_at=datetime.fromisoformat(row[7]) if row[7] else None,
                )

        return None

    def delete(self, key: str) -> bool:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM memory_items WHERE key = ?", (key,))
            row = cursor.fetchone()
            if not row:
                return False

            item_id = row[0]

            cursor.execute("DELETE FROM memory_items WHERE key = ?", (key,))
            cursor.execute("DELETE FROM memory_fts WHERE rowid = (SELECT rowid FROM memory_items WHERE id = ?)", (item_id,))

            conn.commit()

        logger.debug(f"Memory item deleted: {key}")
        return True

    def search(self, query: str) -> List[Dict[str, Any]]:
        results = []

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT mi.id, mi.level, mi.key, mi.value, mi.accessed_at
                FROM memory_items mi
                JOIN memory_fts mf ON mi.rowid = mf.rowid
                WHERE mf MATCH ?
                ORDER BY mi.accessed_at DESC
                LIMIT 20
            """, (query,))

            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "level": row[1],
                    "key": row[2],
                    "value": row[3],
                    "accessed_at": datetime.fromisoformat(row[4]),
                })

        return results

    def get_item_count(self) -> int:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memory_items")
            return cursor.fetchone()[0]

    def cleanup_expired(self) -> int:
        now = datetime.now().isoformat()

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM memory_items WHERE expires_at IS NOT NULL AND expires_at < ?", (now,))
            expired_ids = [row[0] for row in cursor.fetchall()]

            for item_id in expired_ids:
                cursor.execute("DELETE FROM memory_items WHERE id = ?", (item_id,))
                cursor.execute("DELETE FROM memory_fts WHERE rowid = (SELECT rowid FROM memory_items WHERE id = ?)", (item_id,))

            conn.commit()

        logger.info(f"Cleaned up {len(expired_ids)} expired memory items")
        return len(expired_ids)
