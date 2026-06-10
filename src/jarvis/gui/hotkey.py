"""Глобальный хоткей показать/скрыть окно.

Использует пакет `keyboard` (опционально). Если он не установлен — тихо
отключается. Колбэк хоткея выполняется в чужом потоке, поэтому наружу отдаём
Qt-сигнал (потокобезопасно через очередь событий).
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger


class HotkeyManager(QObject):
    triggered = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._active = False

    def start(self) -> bool:
        try:
            import keyboard  # type: ignore
        except ImportError:
            logger.info("Глобальный хоткей недоступен: pip install keyboard")
            return False
        try:
            keyboard.add_hotkey(settings.global_hotkey, lambda: self.triggered.emit())
            self._active = True
            logger.info(f"Глобальный хоткей активен: {settings.global_hotkey}")
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Не удалось зарегистрировать хоткей: {e}")
            return False
