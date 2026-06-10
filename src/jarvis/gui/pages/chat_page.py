"""Страница чата: список диалогов + лента сообщений + поле ввода."""
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from jarvis.gui.bridge import bridge
from jarvis.gui.theme import Colors
from jarvis.gui.widgets.message_bubble import MessageBubble, Role
from jarvis.memory.conversations import Conversation, conversations


class _AutoSizingTextEdit(QTextEdit):
    """QTextEdit, растущий по высоте (1–5 строк); Enter — отправка."""

    send_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTabChangesFocus(True)
        self.document().contentsChanged.connect(self._adjust_height)
        self._adjust_height()

    def _adjust_height(self) -> None:
        doc_height = self.document().size().height()
        h = int(min(max(doc_height + 18, 44), 130))
        self.setFixedHeight(h)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.send_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class _STTWorker(QThread):
    """Записывает с микрофона и распознаёт речь в фоне (vosk)."""

    done = Signal(str)
    failed = Signal(str)

    def run(self) -> None:
        try:
            from jarvis.voice.stt import transcribe_from_mic

            res = transcribe_from_mic(seconds=5.0)
            if res.ok:
                self.done.emit(res.text)
            else:
                self.failed.emit(res.error)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class _ThinkingIndicator(QFrame):
    """Анимированный индикатор «Jarvis думает...»."""

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 6, 20, 6)
        layout.setSpacing(8)
        self.label = QLabel("Jarvis думает")
        self.label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-style: italic; background: transparent;"
        )
        layout.addWidget(self.label)
        layout.addStretch()
        self._dots = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def _tick(self) -> None:
        self._dots = (self._dots + 1) % 4
        self.label.setText("Jarvis думает" + "." * self._dots)

    def start(self) -> None:
        self._dots = 0
        self.label.setText("Jarvis думает")
        self._timer.start(400)
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()


class _ConversationList(QWidget):
    """Панель слева: список диалогов + кнопка «Новый чат»."""

    new_chat = Signal()
    selected = Signal(int)
    deleted = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ConvPanel")
        self.setFixedWidth(232)
        self.setStyleSheet(
            f"#ConvPanel {{ background:{Colors.BG_DARKER}; border-right:1px solid {Colors.BORDER}; }}"
        )
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 12, 10, 12)
        v.setSpacing(8)

        new_btn = QPushButton("+  Новый чат")
        new_btn.setObjectName("Primary")
        new_btn.clicked.connect(self.new_chat.emit)
        v.addWidget(new_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        host = QWidget()
        host.setObjectName("ConvListHost")
        host.setStyleSheet("#ConvListHost { background: transparent; }")
        self._list = QVBoxLayout(host)
        self._list.setContentsMargins(0, 0, 0, 0)
        self._list.setSpacing(3)
        self._list.addStretch()
        scroll.setWidget(host)
        v.addWidget(scroll, stretch=1)

        self._active_id: int | None = None
        self._buttons: dict[int, QPushButton] = {}

    def set_active(self, conv_id: int | None) -> None:
        self._active_id = conv_id
        for cid, btn in self._buttons.items():
            btn.setChecked(cid == conv_id)

    def refresh(self, convs: list[Conversation]) -> None:
        # очищаем список (кроме растяжки в конце)
        while self._list.count() > 1:
            item = self._list.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._buttons = {}

        for conv in convs:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(2)

            tb = QPushButton(conv.title)
            tb.setObjectName("NavButton")
            tb.setCheckable(True)
            tb.setChecked(conv.id == self._active_id)
            tb.setToolTip(conv.title)
            tb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            tb.clicked.connect(lambda _=False, cid=conv.id: self.selected.emit(cid))
            h.addWidget(tb, stretch=1)

            db = QPushButton("✕")
            db.setFixedSize(28, 32)
            db.setToolTip("Удалить чат")
            db.clicked.connect(lambda _=False, cid=conv.id: self.deleted.emit(cid))
            h.addWidget(db)

            self._list.insertWidget(self._list.count() - 1, row)
            self._buttons[conv.id] = tb


class ChatPage(QWidget):
    """Главная страница: диалоги + лента + ввод."""

    def __init__(self) -> None:
        super().__init__()
        self._store = conversations
        self._conv_id: int | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Панель диалогов ---
        self._conv_panel = _ConversationList()
        self._conv_panel.new_chat.connect(self._new_chat)
        self._conv_panel.selected.connect(self._select_conv)
        self._conv_panel.deleted.connect(self._delete_conv)
        root.addWidget(self._conv_panel)

        # --- Колонка чата ---
        chat_col = QWidget()
        col = QVBoxLayout(chat_col)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._messages_container = QWidget()
        self._messages_container.setObjectName("MsgContainer")
        self._messages_container.setStyleSheet(
            f"#MsgContainer {{ background-color: {Colors.BG_DARK}; }}"
        )
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(0, 12, 0, 12)
        self._messages_layout.setSpacing(2)
        self._messages_layout.addStretch()

        self._scroll.setWidget(self._messages_container)
        col.addWidget(self._scroll, stretch=1)

        self._thinking = _ThinkingIndicator()
        col.addWidget(self._thinking)

        # Поле ввода
        input_panel = QFrame()
        input_panel.setStyleSheet(
            f"background-color: {Colors.BG_DARK}; border-top: 1px solid {Colors.BORDER};"
        )
        input_layout = QHBoxLayout(input_panel)
        input_layout.setContentsMargins(16, 12, 16, 16)
        input_layout.setSpacing(10)

        # Голосовой ввод (микрофон) — голос ПОЛЬЗОВАТЕЛЯ
        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setFixedSize(40, 40)
        self._mic_btn.setToolTip("Голосовой ввод (5 секунд)")
        self._mic_btn.clicked.connect(self._on_mic)
        input_layout.addWidget(self._mic_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        self._input = _AutoSizingTextEdit()
        self._input.setPlaceholderText(
            "Спросите Jarvis что-нибудь... (Enter — отправить, Shift+Enter — перенос)"
        )
        self._input.send_requested.connect(self._on_send)
        input_layout.addWidget(self._input, stretch=1)

        self._send_btn = QPushButton("➤")
        self._send_btn.setObjectName("Primary")
        self._send_btn.setFixedSize(48, 48)
        self._send_btn.setStyleSheet(
            f"""
            QPushButton#Primary {{
                background-color: {Colors.ACCENT};
                color: {Colors.TEXT_ON_ACCENT};
                border-radius: 24px;
                font-size: 18px;
                font-weight: bold;
                border: none;
            }}
            QPushButton#Primary:hover {{ background-color: {Colors.ACCENT_HOVER}; }}
            QPushButton#Primary:pressed {{ background-color: {Colors.ACCENT_DARK}; }}
            QPushButton#Primary:disabled {{ background-color: {Colors.BG_LIGHT}; color: {Colors.TEXT_MUTED}; }}
            """
        )
        self._send_btn.clicked.connect(self._on_send)
        self._send_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        input_layout.addWidget(self._send_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        col.addWidget(input_panel)
        root.addWidget(chat_col, stretch=1)

        # Состояние стрима
        self._stream_bubble: MessageBubble | None = None
        self._reasoning_bubble: MessageBubble | None = None

        # Мост
        bridge.agent_thinking.connect(self._on_thinking)
        bridge.agent_reasoning.connect(self._on_reasoning)
        bridge.agent_chunk.connect(self._on_chunk)
        bridge.agent_replied.connect(self._on_reply)
        bridge.agent_error.connect(self._on_error)
        bridge.agent_busy_changed.connect(self._on_busy)

        # Загружаем список диалогов и стартуем с нового чата
        self._refresh_panel()
        self._new_chat()

    # ---------- управление диалогами ----------
    def _refresh_panel(self) -> None:
        self._conv_panel.refresh(self._store.list())
        self._conv_panel.set_active(self._conv_id)

    def _clear_messages(self) -> None:
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _welcome(self) -> None:
        self._add_message(
            "Привет! Я Jarvis. Попробуйте: «создай папку проекты», "
            "«какая погода в Москве?», «что сейчас на экране?»",
            Role.SYSTEM,
        )

    def _new_chat(self) -> None:
        self._conv_id = None
        self._stream_bubble = None
        self._reasoning_bubble = None
        self._clear_messages()
        self._welcome()
        bridge.reset_conversation()
        self._conv_panel.set_active(None)

    def _select_conv(self, conv_id: int) -> None:
        self._conv_id = conv_id
        self._stream_bubble = None
        self._reasoning_bubble = None
        self._clear_messages()
        msgs = self._store.messages(conv_id)
        for m in msgs:
            if m.role == "user":
                self._add_message(m.content, Role.USER)
            else:
                self._add_message(m.content, Role.AGENT, markdown=True)
        bridge.load_conversation([{"role": m.role, "content": m.content} for m in msgs])
        self._conv_panel.set_active(conv_id)
        QTimer.singleShot(60, self._scroll_to_bottom)

    def _delete_conv(self, conv_id: int) -> None:
        self._store.delete(conv_id)
        if conv_id == self._conv_id:
            self._new_chat()
        self._refresh_panel()

    def _ensure_conversation(self, first_text: str) -> None:
        if self._conv_id is None:
            title = (first_text[:40] + "…") if len(first_text) > 40 else first_text
            self._conv_id = self._store.create(title=title or "Новый чат")
            self._refresh_panel()

    # ---------- отправка / приём ----------
    def _on_send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._ensure_conversation(text)
        self._store.add_message(self._conv_id, "user", text)
        self._add_message(text, Role.USER)
        self._input.clear()
        bridge.send_message(text)

    def _on_thinking(self) -> None:
        self._thinking.start()

    def _on_busy(self, busy: bool) -> None:
        self._send_btn.setEnabled(not busy)
        if not busy:
            self._thinking.stop()

    def _on_reasoning(self, chunk: str) -> None:
        if self._reasoning_bubble is None:
            self._thinking.stop()
            self._reasoning_bubble = MessageBubble("🧠 ", Role.SYSTEM)
            self._messages_layout.insertWidget(
                self._messages_layout.count() - 1, self._reasoning_bubble
            )
        self._reasoning_bubble.append_text(chunk)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _on_chunk(self, chunk: str) -> None:
        if self._stream_bubble is None:
            self._thinking.stop()
            self._reasoning_bubble = None
            self._stream_bubble = MessageBubble("", Role.AGENT)
            self._messages_layout.insertWidget(
                self._messages_layout.count() - 1, self._stream_bubble
            )
        self._stream_bubble.append_text(chunk)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _on_reply(self, text: str) -> None:
        self._thinking.stop()
        self._reasoning_bubble = None
        if self._stream_bubble is not None:
            self._stream_bubble.set_text(text, markdown=True)
            self._stream_bubble = None
            QTimer.singleShot(50, self._scroll_to_bottom)
        else:
            self._add_message(text, Role.AGENT, markdown=True)
        # сохраняем ответ в историю чата
        if self._conv_id is not None:
            self._store.add_message(self._conv_id, "assistant", text)
        # озвучка Джарвиса (управляется в Настройках: TTS_ENABLED)
        from jarvis.core.config import settings

        if settings.tts_enabled:
            from jarvis.voice import tts

            tts.speak(text)

    def _on_mic(self) -> None:
        """Голосовой ввод: запись 5с + распознавание в фоне."""
        self._mic_btn.setEnabled(False)
        self._mic_btn.setText("●")
        self._stt = _STTWorker()
        self._stt.done.connect(self._on_stt_done)
        self._stt.failed.connect(self._on_stt_failed)
        self._stt.start()

    def _on_stt_done(self, text: str) -> None:
        self._mic_btn.setEnabled(True)
        self._mic_btn.setText("🎤")
        if text:
            self._input.setPlainText(text)
            self._input.setFocus()
        else:
            self._add_message("🎤 Речь не распознана, попробуйте ещё раз.", Role.SYSTEM)

    def _on_stt_failed(self, error: str) -> None:
        self._mic_btn.setEnabled(True)
        self._mic_btn.setText("🎤")
        self._add_message(f"🎤 {error}", Role.SYSTEM)

    def _on_error(self, message: str) -> None:
        self._thinking.stop()
        self._stream_bubble = None
        self._reasoning_bubble = None
        self._add_message(f"⚠️ {message}", Role.SYSTEM)

    def _add_message(self, text: str, role: Role, markdown: bool = False) -> None:
        bubble = MessageBubble("" if markdown else text, role)
        if markdown:
            bubble.set_text(text, markdown=True)
        self._messages_layout.insertWidget(self._messages_layout.count() - 1, bubble)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())
