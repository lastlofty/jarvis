"""Боковая навигация: список вкладок (чат, экран, настройки)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class Sidebar(QFrame):
    """Узкая колонка слева с кнопками-вкладками."""

    page_selected = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        # Логотип в стиле терминала
        logo = QLabel("λ jarvis_")
        logo.setObjectName("SidebarLogo")
        logo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(logo)

        layout.addSpacing(8)

        # Группа кнопок (чтобы было ровно одна активна)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        items = [
            ("💬   Чат", 0),
            ("🖥   Экран ПК", 1),
            ("⚙   Настройки", 2),
        ]
        for text, index in items:
            btn = QPushButton(text)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda _checked, i=index: self.page_selected.emit(i))
            self._group.addButton(btn, index)
            layout.addWidget(btn)

        # По умолчанию выбран первый
        self._group.button(0).setChecked(True)

        layout.addStretch()

        # Подвал — версия
        version_label = QLabel("v0.1.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #5a6a7d; font-size: 10px; padding: 8px;")
        layout.addWidget(version_label)

    def select(self, index: int) -> None:
        btn = self._group.button(index)
        if btn:
            btn.setChecked(True)
