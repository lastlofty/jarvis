"""Встроенный запуск сервера для мобильного приложения из GUI.

Поднимает FastAPI (uvicorn) в фоновом потоке, чтобы телефон мог подключиться к
тому же компьютеру по локальной сети. Observer/расширения идемпотентны, поэтому
безопасно работает рядом с GUI.
"""
from __future__ import annotations

import socket
import threading

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger

_thread: threading.Thread | None = None


def local_ip() -> str:
    """IP компьютера в локальной сети (для адреса в телефоне)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def url() -> str:
    return f"http://{local_ip()}:{settings.port}/app/"


def is_running() -> bool:
    return _thread is not None and _thread.is_alive()


def start() -> str:
    """Запускает сервер в фоне (если ещё не запущен). Возвращает URL для телефона."""
    global _thread
    if is_running():
        return url()

    def _run() -> None:
        import asyncio

        import uvicorn

        from jarvis.server.api import app

        config = uvicorn.Config(app, host="0.0.0.0", port=settings.port, log_level="warning")
        server = uvicorn.Server(config)
        # off-main-thread: отключаем обработчики сигналов (иначе ошибка)
        server.install_signal_handlers = lambda: None  # type: ignore[method-assign]
        try:
            asyncio.run(server.serve())
        except Exception as e:  # noqa: BLE001
            logger.error(f"Мобильный сервер остановлен: {e}")

    _thread = threading.Thread(target=_run, daemon=True, name="MobileServer")
    _thread.start()
    logger.info(f"Мобильный сервер запущен: {url()}")
    return url()
