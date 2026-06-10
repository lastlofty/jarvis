"""Хранилище множественных диалогов (как чаты в ChatGPT).

SQLite-таблицы conversations + messages. Хранит отображаемые сообщения
(user/assistant); контекст модели восстанавливается из них при переключении.
"""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jarvis.core.config import settings


@dataclass
class Conversation:
    id: int
    title: str
    updated_at: str


@dataclass
class StoredMessage:
    role: str  # "user" | "assistant"
    content: str
    ts: str


class ConversationStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.path = Path(db_path or settings.chats_db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conv_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    FOREIGN KEY(conv_id) REFERENCES conversations(id)
                );
                """
            )
            self._conn.commit()

    def create(self, title: str = "Новый чат") -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO conversations(title, created_at, updated_at) VALUES (?,?,?)",
                (title, now, now),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def list(self) -> list[Conversation]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, title, updated_at FROM conversations ORDER BY updated_at DESC"
            ).fetchall()
        return [Conversation(r["id"], r["title"], r["updated_at"]) for r in rows]

    def add_message(self, conv_id: int, role: str, content: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            self._conn.execute(
                "INSERT INTO messages(conv_id, role, content, ts) VALUES (?,?,?,?)",
                (conv_id, role, content, now),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_at=? WHERE id=?", (now, conv_id)
            )
            self._conn.commit()

    def messages(self, conv_id: int) -> list[StoredMessage]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT role, content, ts FROM messages WHERE conv_id=? ORDER BY id",
                (conv_id,),
            ).fetchall()
        return [StoredMessage(r["role"], r["content"], r["ts"]) for r in rows]

    def rename(self, conv_id: int, title: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE conversations SET title=? WHERE id=?", (title[:80], conv_id)
            )
            self._conn.commit()

    def delete(self, conv_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM messages WHERE conv_id=?", (conv_id,))
            self._conn.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
            self._conn.commit()


# Singleton
conversations = ConversationStore()
