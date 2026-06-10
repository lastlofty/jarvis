"""Observer: сенсорный слой агента.

Отслеживает активное окно и пишет статистику использования
приложений в SQLite. Кросс-платформенный (Windows основной, но Linux/macOS
тоже частично работают для отладки).
"""
from __future__ import annotations

import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger
from jarvis.memory.db import db


# pygetwindow на Windows работает, на Linux — заглушки
try:
    import pygetwindow as gw  # type: ignore
except Exception:  # pragma: no cover
    gw = None  # type: ignore

# pywin32 — только на Windows. Используем для имени exe активного окна.
_IS_WINDOWS = sys.platform == "win32"
if _IS_WINDOWS:  # pragma: no cover - depends on platform
    try:
        import win32gui  # type: ignore
        import win32process  # type: ignore
    except Exception:
        win32gui = None  # type: ignore
        win32process = None  # type: ignore
else:
    win32gui = None  # type: ignore
    win32process = None  # type: ignore


class Observer:
    """Периодически опрашивает активное окно и фиксирует сессии в БД."""

    def __init__(self, interval: float | None = None) -> None:
        self.interval = interval if interval is not None else settings.observer_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._current_session_id: int | None = None
        self._current_app: str | None = None

    # ---------- public API (синхронно дергается LLM-инструментами) ----------

    def get_active_window_title(self) -> str:
        """Заголовок активного окна. '' если не удалось получить."""
        if _IS_WINDOWS and win32gui is not None:
            try:
                hwnd = win32gui.GetForegroundWindow()
                return str(win32gui.GetWindowText(hwnd) or "")
            except Exception as e:
                logger.debug(f"win32 active title failed: {e}")
        if gw is not None:
            try:
                w = gw.getActiveWindow()
                return str(w.title) if w else ""
            except Exception:
                return ""
        return ""

    def get_foreground_process(self) -> str:
        """Имя exe активного окна (например 'chrome.exe'). '' если неизвестно."""
        if _IS_WINDOWS and win32gui is not None and win32process is not None:
            try:
                hwnd = win32gui.GetForegroundWindow()
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                return psutil.Process(pid).name()
            except Exception as e:
                logger.debug(f"foreground process failed: {e}")
                return ""
        # Fallback: процесс с максимумом CPU
        try:
            top = max(
                psutil.process_iter(["name", "cpu_percent"]),
                key=lambda p: p.info["cpu_percent"] or 0.0,
            )
            return str(top.info["name"] or "")
        except Exception:
            return ""

    def list_running_apps(self) -> list[dict[str, Any]]:
        """Список запущенных процессов: имя + PID."""
        out: list[dict[str, Any]] = []
        for p in psutil.process_iter(["pid", "name"]):
            try:
                out.append({"pid": p.info["pid"], "name": p.info["name"] or ""})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return out

    def get_file_tree(self, path: str | Path, max_depth: int = 2) -> str:
        """Дерево файлов и папок в текстовом виде."""
        root = Path(path).expanduser().resolve()
        if not root.exists():
            return f"[не найдено] {root}"

        lines: list[str] = [str(root)]

        def walk(p: Path, depth: int, prefix: str) -> None:
            if depth > max_depth:
                return
            try:
                entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
            except PermissionError:
                lines.append(prefix + "└── [доступ запрещён]")
                return
            for i, child in enumerate(entries):
                connector = "└── " if i == len(entries) - 1 else "├── "
                lines.append(prefix + connector + child.name)
                if child.is_dir():
                    extension = "    " if i == len(entries) - 1 else "│   "
                    walk(child, depth + 1, prefix + extension)

        walk(root, 1, "")
        return "\n".join(lines)

    def get_app_usage(self, start: datetime, end: datetime) -> list[dict[str, Any]]:
        """Агрегированная статистика времени в приложениях."""
        return db.query_app_usage(start, end)

    # ---------- background loop ----------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="Observer")
        self._thread.start()
        logger.info(f"Observer started (interval={self.interval}s)")

    def stop(self) -> None:
        self._stop_event.set()
        # Закрываем последнюю активную сессию
        if self._current_session_id is not None:
            db.close_session(self._current_session_id)
            self._current_session_id = None
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Observer stopped")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.exception(f"Observer tick error: {e}")
            self._stop_event.wait(self.interval)

    def _tick(self) -> None:
        proc = self.get_foreground_process() or "unknown"
        title = self.get_active_window_title()
        if proc != self._current_app:
            # Сменилось приложение — закрыть старую запись, открыть новую
            if self._current_session_id is not None:
                db.close_session(self._current_session_id)
            self._current_session_id = db.open_session(proc, title)
            self._current_app = proc
            logger.debug(f"App switched -> {proc} ({title!r})")


# Singleton
observer = Observer()
