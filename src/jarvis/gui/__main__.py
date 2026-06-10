"""Точка входа: запуск GUI.

Запуск: python -m jarvis.gui
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Когда запущено как собранный .exe — работаем из папки рядом с exe,
# чтобы .env, plugins/, data/ лежали рядом и были доступны/редактируемы.
if getattr(sys, "frozen", False):
    os.chdir(Path(sys.executable).resolve().parent)

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from jarvis.core.config import settings
from jarvis.core.logging_setup import setup_logging
from jarvis.gui.bridge import bridge
from jarvis.gui.main_window import MainWindow
from jarvis.gui.theme import GLOBAL_QSS
from jarvis.observer.observer import observer


def main() -> int:
    setup_logging()

    # На Windows важно задать AppID, иначе таскбар группирует с python.exe
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("jarvis.ai.agent")
        except Exception:
            pass

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Jarvis")
    app.setOrganizationName("Jarvis")
    app.setQuitOnLastWindowClosed(False)  # чтобы трей удерживал процесс

    # Глобальный шрифт
    app.setFont(QFont("Segoe UI", 9))

    # Глобальный QSS
    app.setStyleSheet(GLOBAL_QSS)

    # Запускаем фоновые сервисы
    if settings.enable_observer:
        observer.start()
    bridge.start()

    # Окно
    window = MainWindow()
    window.show()

    exit_code = app.exec()

    # Корректное завершение
    observer.stop()
    bridge.stop()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
