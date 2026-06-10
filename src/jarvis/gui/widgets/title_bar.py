"""Кастомный заголовок окна (в стиле Steam/Discord).

Заменяет стандартный заголовок Windows на свой:
 - логотип + название слева
 - индикатор статуса подключения
 - кнопки свернуть / развернуть / закрыть справа
 - перетаскивание окна за заголовок
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from jarvis.gui.theme import Colors


class StatusDot(QWidget):
    """Цветной кружок статуса подключения."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(8, 8)
        self._color = Colors.TEXT_MUTED
        self._update_style()

    def set_status(self, status: str) -> None:
        """status: 'online' | 'connecting' | 'offline' | 'error'"""
        self._color = {
            "online": Colors.SUCCESS,
            "connecting": Colors.WARNING,
            "offline": Colors.TEXT_MUTED,
            "error": Colors.ERROR,
        }.get(status, Colors.TEXT_MUTED)
        self._update_style()

    def _update_style(self) -> None:
        self.setStyleSheet(
            f"background-color: {self._color}; border-radius: 4px;"
        )


class TitleBar(QFrame):
    """Кастомный title-bar высотой 36px."""

    minimize_requested = Signal()
    maximize_toggled = Signal()
    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._drag_start: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(0)

        # Логотип-эмодзи + название
        logo = QLabel("🤖")
        logo.setStyleSheet("font-size: 16px; background: transparent;")
        layout.addWidget(logo)

        layout.addSpacing(8)

        title = QLabel("Jarvis")
        title.setObjectName("TitleText")
        layout.addWidget(title)

        layout.addSpacing(14)

        # Статус подключения
        self.status_dot = StatusDot()
        layout.addWidget(self.status_dot)
        layout.addSpacing(6)

        self.status_label = QLabel("offline")
        self.status_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; background: transparent;"
        )
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Кнопки: minimize / maximize / close
        btn_min = self._make_btn("─", "Свернуть")
        btn_min.clicked.connect(self.minimize_requested)

        self.btn_max = self._make_btn("□", "Развернуть")
        self.btn_max.clicked.connect(self.maximize_toggled)

        btn_close = self._make_btn("✕", "Закрыть")
        btn_close.setObjectName("CloseBtn")
        btn_close.clicked.connect(self.close_requested)

        layout.addWidget(btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(btn_close)

    @staticmethod
    def _make_btn(text: str, tooltip: str) -> QPushButton:
        b = QPushButton(text)
        b.setToolTip(tooltip)
        b.setCursor(Qt.CursorShape.ArrowCursor)
        b.setFlat(True)
        b.setIconSize(QSize(16, 16))
        return b

    def set_connection_status(self, status: str, label: str) -> None:
        self.status_dot.set_status(status)
        self.status_label.setText(label)

    # --- Перетаскивание окна за title-bar ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start is not None and self.window() is not None:
            window = self.window()
            if window.isMaximized():
                # При перетаскивании из развёрнутого — снимаем максимизацию
                window.showNormal()
            delta = event.globalPosition().toPoint() - self._drag_start
            window.move(window.pos() + delta)
            self._drag_start = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.maximize_toggled.emit()
        super().mouseDoubleClickEvent(event)
