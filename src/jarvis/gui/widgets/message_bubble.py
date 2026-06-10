"""Пузырёк одного сообщения чата."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from jarvis.gui.theme import Colors


class Role(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class MessageBubble(QFrame):
    """Скруглённый пузырёк сообщения с временем."""

    def __init__(self, text: str, role: Role) -> None:
        super().__init__()
        self.role = role
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        bg, fg = self._colors_for(role)

        # Корневой контейнер — чтобы выровнять пузырь по краю
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 4, 12, 4)
        outer.setSpacing(0)

        # Сам пузырь — отдельный фрейм со стилем
        bubble = QFrame()
        bubble.setObjectName("Bubble")
        bubble.setStyleSheet(
            f"""
            #Bubble {{
                background-color: {bg};
                border-radius: 14px;
                padding: 0;
            }}
            """
        )
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(14, 10, 14, 8)
        layout.setSpacing(4)

        # Текст
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setTextFormat(Qt.TextFormat.RichText)
        text_label.setOpenExternalLinks(True)
        text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        text_label.setStyleSheet(
            f"color: {fg}; font-size: 13.5px; line-height: 1.4; background: transparent;"
        )
        text_label.setMaximumWidth(520)
        layout.addWidget(text_label)
        self._text_label = text_label
        self._text = text

        # Время
        time_label = QLabel(datetime.now().strftime("%H:%M"))
        time_label.setStyleSheet(
            f"color: {self._timestamp_color(role)}; font-size: 10px; background: transparent;"
        )
        time_label.setAlignment(
            Qt.AlignmentFlag.AlignRight if role == Role.USER else Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(time_label)

        # Выравнивание пузыря
        if role == Role.USER:
            outer.addStretch()
            outer.addWidget(bubble)
        elif role == Role.AGENT:
            outer.addWidget(bubble)
            outer.addStretch()
        else:  # SYSTEM
            outer.addStretch()
            outer.addWidget(bubble)
            outer.addStretch()

    def append_text(self, chunk: str) -> None:
        """Дописывает кусочек текста (для потокового ответа, plain)."""
        self._text += chunk
        # во время стрима показываем как есть (быстро, без перерендера markdown)
        self._text_label.setTextFormat(Qt.TextFormat.PlainText)
        self._text_label.setText(self._text)

    def set_text(self, text: str, markdown: bool = False) -> None:
        self._text = text
        if markdown:
            from jarvis.gui.markdown_render import markdown_to_html

            self._text_label.setTextFormat(Qt.TextFormat.RichText)
            self._text_label.setText(markdown_to_html(text))
        else:
            self._text_label.setText(text)

    @staticmethod
    def _colors_for(role: Role) -> tuple[str, str]:
        if role == Role.USER:
            return Colors.BUBBLE_USER, Colors.TEXT_ON_ACCENT
        if role == Role.AGENT:
            return Colors.BUBBLE_AGENT, Colors.TEXT_PRIMARY
        return Colors.BUBBLE_SYSTEM, Colors.TEXT_SECONDARY

    @staticmethod
    def _timestamp_color(role: Role) -> str:
        if role == Role.USER:
            return "rgba(4, 19, 11, 0.6)"
        return Colors.TEXT_MUTED
