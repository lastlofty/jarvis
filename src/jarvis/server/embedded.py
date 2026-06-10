"""Встроенный запуск сервера для мобильного приложения из GUI.

Поднимает FastAPI (uvicorn) в фоновом потоке, чтобы телефон мог подключиться к
тому же компьютеру по локальной сети. Observer/расширения идемпотентны, поэтому
безопасно работает рядом с GUI.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import threading

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger

_thread: threading.Thread | None = None

_FW_RULE = "Jarvis Mobile"


def firewall_rule_exists() -> bool:
    """Есть ли уже правило брандмауэра для порта (Windows)."""
    if sys.platform != "win32":
        return True
    try:
        r = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={_FW_RULE}"],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and "localport" in r.stdout.lower()
    except Exception:  # noqa: BLE001
        return False


def add_firewall_rule_elevated() -> bool:
    """Добавляет правило брандмауэра (порт settings.port) с запросом прав админа.

    Вызовет окно UAC. Возвращает True, если запрос отправлен.
    """
    if sys.platform != "win32":
        return False
    if firewall_rule_exists():
        return True
    try:
        import ctypes

        args = (
            f'advfirewall firewall add rule name="{_FW_RULE}" '
            f"dir=in action=allow protocol=TCP localport={settings.port}"
        )
        # runas -> запрос прав администратора (UAC)
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", "netsh", args, None, 0)
        return int(rc) > 32
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Не удалось добавить правило брандмауэра: {e}")
        return False


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


def is_serving(timeout: float = 5.0) -> bool:
    """Проверяет, что сервер реально отвечает на localhost (поднялся ли)."""
    import time

    import httpx

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"http://127.0.0.1:{settings.port}/health", timeout=1.0)
            if r.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.4)
    return False


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
