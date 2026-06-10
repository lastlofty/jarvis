"""Провайдер GLM (Zhipu AI / z.ai) — основная модель.

Использует OpenAI-совместимый эндпоинт open.bigmodel.cn/api/paas/v4.
Бесплатная модель: glm-4-flash. Поддерживает function calling.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator

import httpx

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger
from jarvis.llm.providers.base import (
    LLMProvider,
    LLMResponse,
    Message,
    StreamEvent,
    ToolCall,
)


class GLMProvider(LLMProvider):
    """Тонкая обёртка над OpenAI-совместимым API GLM."""

    def __init__(self) -> None:
        if not settings.glm_api_key:
            raise RuntimeError(
                "GLM_API_KEY не установлен. Получите бесплатный ключ на "
                "https://open.bigmodel.cn/ (модель glm-4-flash бесплатна) "
                "и пропишите в .env"
            )
        self.thinking = settings.glm_thinking
        # при включённом мышлении используем reasoning-модель
        self.model = settings.glm_thinking_model if self.thinking else settings.glm_model
        self.base_url = settings.glm_base_url.rstrip("/")
        self.display_name = f"GLM · {self.model}" + (" 🧠" if self.thinking else "")
        self._headers = {
            "Authorization": f"Bearer {settings.glm_api_key}",
            "Content-Type": "application/json",
        }

    def _base_payload(self, messages: list[Message], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.6,
        }
        if self.thinking:
            payload["thinking"] = {"type": "enabled"}
        if tools:
            payload["tools"] = self.to_openai_tools(tools)
            payload["tool_choice"] = "auto"
        return payload

    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        payload = self._base_payload(messages, tools)

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers,
                json=payload,
            )
        if resp.status_code != 200:
            logger.error(f"GLM API {resp.status_code}: {resp.text[:500]}")
            return LLMResponse(text=f"⚠️ GLM API ошибка {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message", {})

        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                    name=fn.get("name", ""),
                    arguments=args,
                )
            )

        return LLMResponse(
            text=msg.get("content") or "",
            tool_calls=tool_calls,
            reasoning=msg.get("reasoning_content") or "",
        )

    async def stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> AsyncIterator[StreamEvent]:
        payload = self._base_payload(messages, tools)
        payload["stream"] = True

        full_text = ""
        full_reasoning = ""
        # накопление tool_calls по индексу: idx -> {id, name, args}
        tc_acc: dict[int, dict[str, str]] = {}

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                ) as resp:
                    if resp.status_code != 200:
                        body = (await resp.aread()).decode("utf-8", "ignore")
                        logger.error(f"GLM stream {resp.status_code}: {body[:300]}")
                        yield StreamEvent(
                            kind="final",
                            response=LLMResponse(
                                text=f"⚠️ GLM API ошибка {resp.status_code}: {body[:200]}"
                            ),
                        )
                        return

                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        delta = (chunk.get("choices") or [{}])[0].get("delta", {})

                        rpiece = delta.get("reasoning_content")
                        if rpiece:
                            full_reasoning += rpiece
                            yield StreamEvent(kind="reasoning", text=rpiece)

                        piece = delta.get("content")
                        if piece:
                            full_text += piece
                            yield StreamEvent(kind="delta", text=piece)

                        for tc in delta.get("tool_calls") or []:
                            idx = tc.get("index", 0)
                            slot = tc_acc.setdefault(idx, {"id": "", "name": "", "args": ""})
                            if tc.get("id"):
                                slot["id"] = tc["id"]
                            fn = tc.get("function", {})
                            if fn.get("name"):
                                slot["name"] = fn["name"]
                            if fn.get("arguments"):
                                slot["args"] += fn["arguments"]
        except httpx.HTTPError as e:
            yield StreamEvent(
                kind="final",
                response=LLMResponse(text=f"⚠️ GLM ошибка соединения: {e}"),
            )
            return

        tool_calls: list[ToolCall] = []
        for idx in sorted(tc_acc):
            slot = tc_acc[idx]
            try:
                args = json.loads(slot["args"]) if slot["args"] else {}
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=slot["id"] or f"call_{uuid.uuid4().hex[:8]}",
                    name=slot["name"],
                    arguments=args,
                )
            )

        yield StreamEvent(
            kind="final",
            response=LLMResponse(
                text=full_text, tool_calls=tool_calls, reasoning=full_reasoning
            ),
        )
