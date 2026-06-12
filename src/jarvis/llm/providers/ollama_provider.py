"""Провайдер Ollama — локальные модели (бесплатно, офлайн).

Использует нативный эндпоинт /api/chat, который с версии 0.3+ поддерживает
function calling через поле `tools`. Качество вызова инструментов зависит от
модели (рекомендуется qwen2.5, llama3.1 и новее).
"""
from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger
from jarvis.llm.providers.base import LLMProvider, LLMResponse, Message, ToolCall


class OllamaProvider(LLMProvider):
    """Обёртка над локальным сервером Ollama."""

    def __init__(self) -> None:
        self.model = settings.ollama_model
        self.host = settings.ollama_host.rstrip("/")
        self.display_name = f"Ollama · {self.model}"

    @staticmethod
    def _to_ollama_messages(messages: list[Message]) -> list[dict[str, Any]]:
        """Приводит историю к нативному формату Ollama.

        Ollama /api/chat ждёт function.arguments как ОБЪЕКТ (а не JSON-строку,
        как в OpenAI-формате), иначе парсер падает с ошибкой про '}'.
        """
        out: list[dict[str, Any]] = []
        for m in messages:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                new_calls = []
                for tc in m["tool_calls"]:
                    fn = tc.get("function", {})
                    args = fn.get("arguments")
                    if isinstance(args, str):
                        try:
                            args = json.loads(args) if args.strip() else {}
                        except json.JSONDecodeError:
                            args = {}
                    new_calls.append({"function": {"name": fn.get("name", ""), "arguments": args}})
                out.append({"role": "assistant", "content": m.get("content", ""),
                            "tool_calls": new_calls})
            else:
                out.append(m)
        return out

    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._to_ollama_messages(messages),
            "stream": False,
        }
        if tools:
            payload["tools"] = self.to_openai_tools(tools)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self.host}/api/chat", json=payload)
        except httpx.ConnectError:
            return LLMResponse(
                text="⚠️ Ollama не запущен. Выполните `ollama serve` и установите модель "
                f"`ollama pull {self.model}`."
            )

        if resp.status_code != 200:
            logger.error(f"Ollama {resp.status_code}: {resp.text[:500]}")
            return LLMResponse(text=f"⚠️ Ollama ошибка {resp.status_code}: {resp.text[:200]}")

        msg = resp.json().get("message", {})

        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                import json

                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append(
                ToolCall(
                    id=f"call_{uuid.uuid4().hex[:8]}",
                    name=fn.get("name", ""),
                    arguments=args,
                )
            )

        return LLMResponse(text=msg.get("content") or "", tool_calls=tool_calls)
