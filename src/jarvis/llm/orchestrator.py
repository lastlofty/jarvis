"""Провайдеро-независимый оркестратор диалога.

Раньше был жёстко завязан на Gemini. Теперь работает поверх любого провайдера
(GLM / Gemini / Ollama) через единый интерфейс `LLMProvider`. Сам ведёт историю,
крутит цикл вызова инструментов и подмешивает знания из RAG.
"""
from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger
from jarvis.core.types import ToolResult
from jarvis.executor import registry
from jarvis.llm.providers import LLMProvider, get_provider
from jarvis.memory.short_term import ShortTermMemory
from jarvis.rag.store import rag

SYSTEM_PROMPT = """Ты — Jarvis, AI-агент для управления Windows. У тебя есть доступ к инструментам, перечисленным в твоей конфигурации функций.
Твоя задача — помогать пользователю, выполняя действия на компьютере.

Правила:
1. При неясности — задавай уточняющие вопросы через ask_user.
2. Разбивай сложные задачи на шаги. Если задача требует НЕСКОЛЬКИХ действий —
   СНАЧАЛА вызови create_plan со списком шагов, затем выполняй их по очереди
   обычными инструментами и отмечай прогресс через complete_step.
3. После выполнения каждого действия кратко сообщай результат пользователю.
4. Если действие не удалось — объясни причину и предложи альтернативу.
5. БЕЗОПАСНОСТЬ: при удалении или перемещении файлов ВСЕГДА сначала вызывай ask_user
   с конкретным вопросом ("Удалить файл X.txt? Это действие необратимо."), и только
   при положительном ответе вызывай delete_file/move_file с confirmed=true.
6. Отвечай по-русски, если пользователь пишет по-русски.
7. Если в сообщении есть блок "Контекст из базы знаний" — используй его как источник
   фактов, но не выдумывай того, чего там нет.
8. ПАМЯТЬ: как только пользователь сообщает о себе что-то важное и долговечное —
   имя, хобби, увлечения, профессию, предпочтения, цели, важные факты — СРАЗУ
   проактивно (без просьбы) вызывай remember с кратким фактом (например:
   "Хобби пользователя — рисование"). Не дублируй уже известное (см. блок
   "Что я помню о пользователе"). Не запоминай мелочи и разовые вопросы.
"""

MAX_TOOL_ITERATIONS = 12
# Сколько сообщений истории (кроме system) держим в контексте модели.
MAX_HISTORY_MESSAGES = 40


class Orchestrator:
    """Управляет диалогом: история + RAG + цикл инструментов поверх провайдера."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_provider()
        self.memory = ShortTermMemory(max_size=20)
        # Нейтральная история для модели (вкл. tool-сообщения)
        self.history: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        logger.info(f"Оркестратор поднят на провайдере: {self.provider.display_name}")

    @property
    def provider_name(self) -> str:
        return self.provider.display_name

    # ---------- RAG + долговременная память ----------
    def _augment_with_rag(self, user_text: str) -> str:
        blocks: list[str] = []

        if settings.rag_enabled:
            hits = rag.search(user_text, k=settings.rag_top_k)
            if hits:
                ctx = "\n\n".join(
                    f"[{i + 1}] (источник: {h.source})\n{h.text}"
                    for i, h in enumerate(hits)
                )
                blocks.append(f"Контекст из базы знаний:\n{ctx}")
                logger.info(f"RAG подмешал {len(hits)} фрагментов")

        if settings.memory_enabled:
            from jarvis.memory.long_term import long_term

            mem = long_term.recall(user_text)
            if mem:
                facts = "\n".join(f"- {h.text}" for h in mem)
                blocks.append(f"Что я помню о пользователе:\n{facts}")
                logger.info(f"Память подмешала {len(mem)} фактов")

        if not blocks:
            return user_text
        return "\n\n".join(blocks) + f"\n\n---\nВопрос пользователя: {user_text}"

    def _trim_history(self) -> None:
        """Обрезает историю, сохраняя system и валидную структуру.

        Хвост не должен начинаться с 'tool'/'assistant' (иначе у OpenAI-совместимых
        провайдеров tool-сообщение окажется без своего вызова) — отрезаем до
        ближайшего сообщения пользователя.
        """
        system = self.history[0:1]
        body = self.history[1:]
        if len(body) <= MAX_HISTORY_MESSAGES:
            return
        body = body[-MAX_HISTORY_MESSAGES:]
        while body and body[0].get("role") in ("tool", "assistant"):
            body.pop(0)
        self.history = system + body

    # ---------- основной цикл ----------
    async def handle(self, user_text: str) -> str:
        self._trim_history()
        self.memory.add("user", user_text)
        self.history.append({"role": "user", "content": self._augment_with_rag(user_text)})

        try:
            for _ in range(MAX_TOOL_ITERATIONS):
                declarations = registry.all_declarations()
                response = await self.provider.generate(self.history, declarations)

                if not response.wants_tools:
                    text = response.text or "(нет ответа)"
                    self.history.append({"role": "assistant", "content": text})
                    self.memory.add("assistant", text)
                    return text

                # Записываем намерение модели вызвать инструменты
                self.history.append(
                    {
                        "role": "assistant",
                        "content": response.text or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                                },
                            }
                            for tc in response.tool_calls
                        ],
                    }
                )

                # Выполняем и складываем результаты
                for tc in response.tool_calls:
                    logger.info(f"LLM -> {tc.name}({tc.arguments})")
                    result: ToolResult = await registry.dispatch(tc.name, tc.arguments)
                    self.history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": json.dumps(result.to_dict(), ensure_ascii=False),
                        }
                    )

            # превышен лимит итераций
            fallback = "⚠️ Превышен лимит шагов выполнения. Уточните задачу."
            self.history.append({"role": "assistant", "content": fallback})
            return fallback
        except Exception as e:  # noqa: BLE001
            logger.exception("orchestrator")
            return f"⚠️ Ошибка обработки: {e}"

    # ---------- потоковый цикл ----------
    async def handle_stream(
        self,
        user_text: str,
        on_chunk: Callable[[str], Awaitable[None]] | Callable[[str], None],
        on_reasoning: Callable[[str], Awaitable[None]] | Callable[[str], None] | None = None,
    ) -> str:
        """Как handle(), но финальный текст отдаётся по кусочкам через on_chunk.

        on_reasoning (опц.) получает «размышления» модели при глубоком мышлении.
        Возвращает полный финальный текст. Шаги с вызовами инструментов
        не стримятся (там модель обычно не пишет текст).
        """
        import inspect

        async def emit(chunk: str) -> None:
            res = on_chunk(chunk)
            if inspect.isawaitable(res):
                await res

        async def emit_reasoning(chunk: str) -> None:
            if on_reasoning is None:
                return
            res = on_reasoning(chunk)
            if inspect.isawaitable(res):
                await res

        self._trim_history()
        self.memory.add("user", user_text)
        self.history.append({"role": "user", "content": self._augment_with_rag(user_text)})

        try:
            for _ in range(MAX_TOOL_ITERATIONS):
                declarations = registry.all_declarations()
                final = None
                async for ev in self.provider.stream(self.history, declarations):
                    if ev.kind == "reasoning" and ev.text:
                        await emit_reasoning(ev.text)
                    elif ev.kind == "delta" and ev.text:
                        await emit(ev.text)
                    elif ev.kind == "final":
                        final = ev.response

                if final is None:
                    final = await self.provider.generate(self.history, declarations)

                if not final.wants_tools:
                    text = final.text or "(нет ответа)"
                    self.history.append({"role": "assistant", "content": text})
                    self.memory.add("assistant", text)
                    return text

                self.history.append(
                    {
                        "role": "assistant",
                        "content": final.text or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                                },
                            }
                            for tc in final.tool_calls
                        ],
                    }
                )
                for tc in final.tool_calls:
                    logger.info(f"LLM -> {tc.name}({tc.arguments})")
                    result: ToolResult = await registry.dispatch(tc.name, tc.arguments)
                    self.history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": json.dumps(result.to_dict(), ensure_ascii=False),
                        }
                    )

            fallback = "⚠️ Превышен лимит шагов выполнения. Уточните задачу."
            await emit(fallback)
            self.history.append({"role": "assistant", "content": fallback})
            return fallback
        except Exception as e:  # noqa: BLE001
            logger.exception("orchestrator stream")
            err = f"⚠️ Ошибка обработки: {e}"
            await emit(err)
            return err

    def reset(self) -> None:
        """Сбрасывает историю диалога (system-prompt остаётся)."""
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.memory.clear()

    def load_history(self, messages: list[dict[str, str]]) -> None:
        """Восстанавливает контекст из сохранённых сообщений (role/content)."""
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in messages:
            role = m.get("role")
            if role in ("user", "assistant") and m.get("content"):
                self.history.append({"role": role, "content": m["content"]})
        self._trim_history()


# Обратная совместимость со старым кодом (console/api/gui импортировали это имя).
GeminiOrchestrator = Orchestrator
