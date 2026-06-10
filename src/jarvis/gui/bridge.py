"""Мост Qt <-> asyncio.

В Qt главный поток крутит event-loop GUI. asyncio же требует свой event-loop.
Решение: запустить asyncio в отдельном потоке и обмениваться данными через
QThread + сигналы.

Так мы не блокируем UI пока Gemini обрабатывает запрос.
"""
from __future__ import annotations

import asyncio
import threading

from PySide6.QtCore import QObject, Signal


class AgentBridge(QObject):
    """Singleton-мост: GUI шлёт user_message_sent, получает agent_replied."""

    # Сигналы (Qt → внешний мир)
    agent_thinking = Signal()                       # начали обработку
    agent_reasoning = Signal(str)                   # кусочек «размышлений» (deep thinking)
    agent_chunk = Signal(str)                       # кусочек потокового ответа
    agent_replied = Signal(str)                     # пришёл финальный ответ
    agent_error = Signal(str)                       # ошибка
    agent_busy_changed = Signal(bool)               # busy on/off

    def __init__(self) -> None:
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._orchestrator = None
        self._ready_event = threading.Event()

    def start(self) -> None:
        """Запускает asyncio-loop в отдельном потоке."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="AsyncBridge")
        self._thread.start()
        # Ждём, пока loop инициализируется
        self._ready_event.wait(timeout=10.0)

    def stop(self) -> None:
        """Корректно останавливает loop."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def send_message(self, text: str) -> None:
        """GUI вызывает это, когда пользователь нажал Enter.

        Метод вернётся мгновенно — обработка в фоне, результат придёт сигналом.
        """
        if not self._loop or not self._loop.is_running():
            self.agent_error.emit("Async-loop ещё не запущен")
            return
        self.agent_thinking.emit()
        self.agent_busy_changed.emit(True)
        asyncio.run_coroutine_threadsafe(self._handle(text), self._loop)

    def reset_conversation(self) -> None:
        """Новый чат: очищает контекст оркестратора."""
        if self._loop and self._orchestrator is not None:
            self._loop.call_soon_threadsafe(self._orchestrator.reset)

    def load_conversation(self, messages: list[dict]) -> None:
        """Загружает контекст выбранного чата в оркестратор."""
        if self._loop and self._orchestrator is not None:
            self._loop.call_soon_threadsafe(self._orchestrator.load_history, messages)

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Запускаем стартовую инициализацию
        self._loop.create_task(self._init_orchestrator())
        self._ready_event.set()

        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    async def _init_orchestrator(self) -> None:
        """Создаёт оркестратор внутри event-loop'а (нужно для async)."""
        try:
            # Локальный импорт — иначе при `pyinstaller --collect-all` тащится
            # GUI там, где не надо
            from jarvis.bootstrap import load_extensions, start_mcp
            from jarvis.llm.orchestrator import Orchestrator

            load_extensions()
            await start_mcp()
            self._orchestrator = Orchestrator()
        except Exception as e:
            self.agent_error.emit(f"Не удалось инициализировать оркестратор:\n{e}")

    async def _handle(self, text: str) -> None:
        try:
            if self._orchestrator is None:
                self.agent_error.emit("Оркестратор не инициализирован")
                return

            def on_chunk(chunk: str) -> None:
                # Qt-сигналы потокобезопасны: эмитим из asyncio-потока
                self.agent_chunk.emit(chunk)

            def on_reasoning(chunk: str) -> None:
                self.agent_reasoning.emit(chunk)

            answer = await self._orchestrator.handle_stream(text, on_chunk, on_reasoning)
            self.agent_replied.emit(answer)
        except Exception as e:
            self.agent_error.emit(f"Ошибка: {e}")
        finally:
            self.agent_busy_changed.emit(False)


# Singleton — импортируется со всех сторон
bridge = AgentBridge()
