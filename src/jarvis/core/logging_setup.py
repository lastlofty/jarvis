"""Централизованная настройка логов.

Loguru красив, типизирован и удобен для асинхронного кода.

Важно: в windowed-сборке PyInstaller (console=False) sys.stderr равен None,
поэтому добавление stderr-приёмника без проверки приводит к падению.
"""
from __future__ import annotations

import sys

from loguru import logger

from jarvis.core.config import settings


def setup_logging() -> None:
    """Перенастраивает loguru: stderr (если есть) + файл с ротацией."""
    logger.remove()

    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}:{function}:{line}</cyan> | "
        "<level>{message}</level>"
    )

    # В windowed-режиме (PyInstaller console=False) sys.stderr == None.
    # Добавляем stderr-приёмник только если он реально существует.
    if sys.stderr is not None:
        try:
            logger.add(sys.stderr, level=settings.log_level, format=fmt, colorize=True)
        except (TypeError, ValueError):
            # На всякий случай: некоторые экзотические окружения
            # подменяют stderr на нечто, что loguru не принимает.
            pass

    # Файл — ВСЕГДА. Это наш единственный надёжный канал в windowed-сборке.
    logger.add(
        settings.log_file,
        level=settings.log_level,
        rotation="10 MB",
        retention="14 days",
        encoding="utf-8",
        format=fmt,
    )


__all__ = ["logger", "setup_logging"]
