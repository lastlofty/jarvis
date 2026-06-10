"""Базовый интерфейс провайдера LLM.

Все провайдеры (GLM, Gemini, Ollama) приводятся к единому интерфейсу, чтобы
оркестратор не зависел от конкретного SDK. Внутренний формат сообщений —
нейтральный (близкий к OpenAI), каждый провайдер сам переводит его в свой.

Провайдеры СТАТЕЛЕСНЫ: оркестратор хранит всю историю и передаёт её целиком
при каждом вызове. Это упрощает переключение моделей на лету.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal


@dataclass
class ToolCall:
    """Запрос модели на вызов инструмента."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Унифицированный ответ модели за один шаг.

    Либо текст (финальный ответ), либо список вызовов инструментов.
    reasoning — «размышления» модели (если включено глубокое мышление).
    """

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    reasoning: str = ""

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


@dataclass
class StreamEvent:
    """Событие потоковой генерации.

    kind="reasoning" -> text содержит кусочек «размышлений» модели;
    kind="delta"     -> text содержит очередной кусочек ответа;
    kind="final"     -> response содержит итоговый ответ (текст + tool_calls).
    """

    kind: Literal["reasoning", "delta", "final"]
    text: str = ""
    response: "LLMResponse | None" = None


# Нейтральное сообщение истории. Совместимо с OpenAI-форматом:
#   {"role": "system"|"user"|"assistant"|"tool", "content": str,
#    "tool_calls": [...]?, "tool_call_id": str?, "name": str?}
Message = dict[str, Any]


class LLMProvider(abc.ABC):
    """Абстрактный провайдер модели."""

    #: человекочитаемое имя, например "GLM-4-Flash"
    display_name: str = "LLM"

    @abc.abstractmethod
    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        """Делает один запрос к модели.

        :param messages: полная история в нейтральном формате (вкл. system).
        :param tools: декларации инструментов (JSON-schema, OpenAI-стиль).
        :return: текст или список вызовов инструментов.
        """
        raise NotImplementedError

    async def stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> AsyncIterator[StreamEvent]:
        """Потоковая генерация. По умолчанию — обёртка над generate (без стрима).

        Провайдеры, поддерживающие SSE (например GLM), переопределяют метод и
        отдают текст по кусочкам через события kind="delta".
        """
        response = await self.generate(messages, tools)
        if response.reasoning:
            yield StreamEvent(kind="reasoning", text=response.reasoning)
        if response.text and not response.tool_calls:
            yield StreamEvent(kind="delta", text=response.text)
        yield StreamEvent(kind="final", response=response)

    @staticmethod
    def to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """JSON-декларации Jarvis -> OpenAI `tools` (для GLM и Ollama)."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                },
            }
            for t in tools
        ]
