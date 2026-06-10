"""SQLite-репозиторий: app_usage, action_log, dialog_history.

Долговременная память с эмбеддингами добавляется отдельным модулем
на следующем этапе (см. docs/ROADMAP.md).
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger


SCHEMA = """
CREATE TABLE IF NOT EXISTS app_usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    app_name    TEXT    NOT NULL,
    window_title TEXT,
    started_at  TEXT    NOT NULL,    -- ISO 8601
    ended_at    TEXT,                -- NULL пока сессия активна
    duration_s  REAL                 -- кэш длительности (сек)
);
CREATE INDEX IF NOT EXISTS idx_app_usage_app ON app_usage(app_name);
CREATE INDEX IF NOT EXISTS idx_app_usage_started ON app_usage(started_at);

CREATE TABLE IF NOT EXISTS action_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    action_name TEXT    NOT NULL,
    parameters  TEXT,                -- JSON
    result      TEXT,                -- JSON
    error       TEXT
);
CREATE INDEX IF NOT EXISTS idx_action_log_ts ON action_log(timestamp);

CREATE TABLE IF NOT EXISTS dialog_history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    role      TEXT NOT NULL,    -- user | assistant | tool
    content   TEXT NOT NULL
);
"""


class Database:
    """Тонкая обёртка над sqlite3 с потокобезопасной выдачей соединений."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or settings.db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connect() as cx:
            cx.executescript(SCHEMA)
            cx.commit()
        logger.info(f"DB initialised at {self.db_path}")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Потокобезопасное соединение с включенными внешними ключами."""
        with self._lock:
            cx = sqlite3.connect(self.db_path, timeout=10.0)
            cx.row_factory = sqlite3.Row
            cx.execute("PRAGMA foreign_keys = ON;")
            try:
                yield cx
            finally:
                cx.close()

    # ---------- app_usage ----------

    def open_session(self, app_name: str, window_title: str) -> int:
        """Открывает запись об использовании приложения. Возвращает её id."""
        now = datetime.utcnow().isoformat()
        with self.connect() as cx:
            cur = cx.execute(
                "INSERT INTO app_usage(app_name, window_title, started_at) "
                "VALUES (?, ?, ?)",
                (app_name, window_title, now),
            )
            cx.commit()
            return int(cur.lastrowid)

    def close_session(self, session_id: int) -> None:
        """Закрывает запись и кэширует длительность."""
        now_dt = datetime.utcnow()
        with self.connect() as cx:
            row = cx.execute(
                "SELECT started_at FROM app_usage WHERE id = ?", (session_id,)
            ).fetchone()
            if row is None:
                return
            started = datetime.fromisoformat(row["started_at"])
            duration = (now_dt - started).total_seconds()
            cx.execute(
                "UPDATE app_usage SET ended_at = ?, duration_s = ? WHERE id = ?",
                (now_dt.isoformat(), duration, session_id),
            )
            cx.commit()

    def query_app_usage(
        self, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        """Агрегирует время по приложениям в диапазоне дат (UTC)."""
        with self.connect() as cx:
            rows = cx.execute(
                """
                SELECT app_name,
                       SUM(COALESCE(duration_s, 0)) AS total_s,
                       COUNT(*) AS sessions
                FROM app_usage
                WHERE started_at >= ? AND started_at < ?
                GROUP BY app_name
                ORDER BY total_s DESC
                """,
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        return [dict(r) for r in rows]

    # ---------- action_log ----------

    def log_action(
        self,
        action_name: str,
        parameters: dict[str, Any] | None,
        result: dict[str, Any] | None,
        error: str | None = None,
    ) -> None:
        with self.connect() as cx:
            cx.execute(
                "INSERT INTO action_log(timestamp, action_name, parameters, result, error) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    datetime.utcnow().isoformat(),
                    action_name,
                    json.dumps(parameters, ensure_ascii=False) if parameters else None,
                    json.dumps(result, ensure_ascii=False) if result else None,
                    error,
                ),
            )
            cx.commit()

    # ---------- dialog_history ----------

    def append_dialog(self, role: str, content: str) -> None:
        with self.connect() as cx:
            cx.execute(
                "INSERT INTO dialog_history(timestamp, role, content) VALUES (?, ?, ?)",
                (datetime.utcnow().isoformat(), role, content),
            )
            cx.commit()


# Singleton
db = Database()
