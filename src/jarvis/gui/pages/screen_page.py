"""Страница просмотра экрана ПК.

Делает скриншот через наш input_tools.take_screenshot и показывает картинку.
Поддерживает ручное и авто-обновление каждые 2 секунды.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from jarvis.gui.theme import Colors


class _ScreenshotWorker(QThread):
    """Делает скриншот в фоновом потоке (mss блокирует ~50-200мс)."""

    done = Signal(str)         # путь к PNG
    failed = Signal(str)       # текст ошибки

    def run(self) -> None:
        try:
            from jarvis.executor.input_tools import take_screenshot
            result = take_screenshot()
            if result.status == "success" and result.data:
                self.done.emit(result.data["path"])
            else:
                self.failed.emit(result.message)
        except Exception as e:
            self.failed.emit(str(e))


class ScreenPage(QWidget):
    """Просмотр текущего рабочего стола."""

    def __init__(self) -> None:
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Заголовок
        header = QHBoxLayout()
        title = QLabel("Экран ПК")
        title.setObjectName("Heading")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        header.addWidget(title)
        header.addStretch()

        # Кнопки
        self._btn_refresh = QPushButton("🔄  Обновить")
        self._btn_refresh.setObjectName("Primary")
        self._btn_refresh.clicked.connect(self._refresh)
        header.addWidget(self._btn_refresh)

        self._btn_auto = QPushButton("▶  Авто (2 сек)")
        self._btn_auto.setCheckable(True)
        self._btn_auto.toggled.connect(self._toggle_auto)
        header.addWidget(self._btn_auto)
        root.addLayout(header)

        # Информационная строка
        self._info_label = QLabel("Нажмите «Обновить» чтобы получить скриншот")
        self._info_label.setObjectName("Subtitle")
        self._info_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        root.addWidget(self._info_label)

        # Карточка с картинкой
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(2, 2, 2, 2)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {Colors.BG_DARKEST}; border-radius: 8px; border: none; }}"
        )

        self._image_label = QLabel("Скриншот появится здесь")
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 14px; padding: 80px;"
        )
        self._scroll.setWidget(self._image_label)

        card_layout.addWidget(self._scroll)
        root.addWidget(card, stretch=1)

        # Авто-обновление
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._refresh)

        self._worker: _ScreenshotWorker | None = None
        self._current_pixmap: QPixmap | None = None

    def _refresh(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._btn_refresh.setEnabled(False)
        self._info_label.setText("Получаю скриншот...")

        self._worker = _ScreenshotWorker()
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(lambda: self._btn_refresh.setEnabled(True))
        self._worker.start()

    def _on_done(self, path: str) -> None:
        from datetime import datetime

        pixmap = QPixmap(path)
        if pixmap.isNull():
            self._info_label.setText(f"Не удалось загрузить: {path}")
            return

        self._current_pixmap = pixmap
        self._update_displayed_pixmap()
        self._info_label.setText(
            f"Обновлено в {datetime.now().strftime('%H:%M:%S')}  •  "
            f"{pixmap.width()}×{pixmap.height()}  •  {Path(path).name}"
        )

    def _on_failed(self, msg: str) -> None:
        self._info_label.setText(f"Ошибка: {msg}")
        self._image_label.setText("Не удалось получить скриншот")

    def _update_displayed_pixmap(self) -> None:
        """Масштабирует картинку под размер контейнера, сохраняя пропорции."""
        if self._current_pixmap is None:
            return
        viewport = self._scroll.viewport().size()
        # Оставляем небольшой запас
        target = viewport - viewport * 0.04
        scaled = self._current_pixmap.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)
        self._image_label.setStyleSheet("background: transparent; padding: 0;")

    def _toggle_auto(self, on: bool) -> None:
        if on:
            self._btn_auto.setText("⏸  Остановить авто")
            self._auto_timer.start(2000)
            self._refresh()
        else:
            self._btn_auto.setText("▶  Авто (2 сек)")
            self._auto_timer.stop()

    def resizeEvent(self, event) -> None:  # noqa: ANN001 — Qt event type
        super().resizeEvent(event)
        # Перерисовываем при ресайзе
        self._update_displayed_pixmap()
