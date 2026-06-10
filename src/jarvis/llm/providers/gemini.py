"""Провайдер Gemini (google-generativeai).

Переводит нейтральную историю сообщений в формат `contents` Gemini и делает
stateless-запрос generate_content с function calling.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import google.generativeai as genai

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger
from jarvis.llm.providers.base import LLMProvider, LLMResponse, Message, ToolCall


class GeminiProvider(LLMProvider):
    """Обёртка над Gemini SDK c приведением к общему интерфейсу."""

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY не установлен. Получите ключ на "
                "https://aistudio.google.com/app/apikey и пропишите в .env"
            )
        genai.configure(api_key=settings.gemini_api_key)
        self.model_name = settings.gemini_model
        self.display_name = f"Gemini · {self.model_name}"

    # ---- конвертация схемы инструментов ----
    @staticmethod
    def _convert_schema(schema: dict[str, Any]) -> Any:
        if not schema:
            return genai.protos.Schema(type=genai.protos.Type.OBJECT, properties={})
        type_map = {
            "object": genai.protos.Type.OBJECT,
            "string": genai.protos.Type.STRING,
            "integer": genai.protos.Type.INTEGER,
            "number": genai.protos.Type.NUMBER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
        }

        def conv(s: dict[str, Any]) -> genai.protos.Schema:
            t = s.get("type", "string")
            kwargs: dict[str, Any] = {"type": type_map.get(t, genai.protos.Type.STRING)}
            if "description" in s:
                kwargs["description"] = s["description"]
            if "enum" in s:
                kwargs["enum"] = s["enum"]
            if t == "object":
                kwargs["properties"] = {
                    k: conv(v) for k, v in s.get("properties", {}).items()
                }
                if s.get("required"):
                    kwargs["required"] = s["required"]
            elif t == "array" and "items" in s:
                kwargs["items"] = conv(s["items"])
            return genai.protos.Schema(**kwargs)

        return conv(schema)

    def _build_tools(self, tools: list[dict[str, Any]]) -> list:
        if not tools:
            return []
        decls = [
            genai.protos.FunctionDeclaration(
                name=t["name"],
                description=t.get("description", ""),
                parameters=self._convert_schema(t.get("parameters", {})),
            )
            for t in tools
        ]
        return [genai.protos.Tool(function_declarations=decls)]

    # ---- конвертация истории ----
    @staticmethod
    def _split_system(messages: list[Message]) -> tuple[str, list[Message]]:
        system_chunks = [m["content"] for m in messages if m.get("role") == "system"]
        rest = [m for m in messages if m.get("role") != "system"]
        return "\n".join(system_chunks), rest

    def _to_contents(self, messages: list[Message]) -> list:
        contents = []
        for m in messages:
            role = m.get("role")
            if role == "user":
                contents.append(
                    genai.protos.Content(
                        role="user", parts=[genai.protos.Part(text=m.get("content", ""))]
                    )
                )
            elif role == "assistant":
                parts = []
                if m.get("content"):
                    parts.append(genai.protos.Part(text=m["content"]))
                for tc in m.get("tool_calls") or []:
                    fn = tc["function"]
                    args = fn.get("arguments") or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    parts.append(
                        genai.protos.Part(
                            function_call=genai.protos.FunctionCall(
                                name=fn["name"], args=args
                            )
                        )
                    )
                if parts:
                    contents.append(genai.protos.Content(role="model", parts=parts))
            elif role == "tool":
                contents.append(
                    genai.protos.Content(
                        role="user",
                        parts=[
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=m.get("name", "tool"),
                                    response={"result": m.get("content", "")},
                                )
                            )
                        ],
                    )
                )
        return contents

    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        system, rest = self._split_system(messages)
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system or None,
            tools=self._build_tools(tools),
        )
        contents = self._to_contents(rest)
        try:
            response = await asyncio.to_thread(model.generate_content, contents)
        except Exception as e:  # noqa: BLE001
            logger.exception("gemini generate")
            return LLMResponse(text=f"⚠️ Gemini ошибка: {e}")

        text_chunks: list[str] = []
        tool_calls: list[ToolCall] = []
        for cand in getattr(response, "candidates", []) or []:
            for part in cand.content.parts:
                fc = getattr(part, "function_call", None)
                if fc and fc.name:
                    tool_calls.append(
                        ToolCall(
                            id=f"call_{uuid.uuid4().hex[:8]}",
                            name=fc.name,
                            arguments={k: v for k, v in fc.args.items()} if fc.args else {},
                        )
                    )
                elif getattr(part, "text", None):
                    text_chunks.append(part.text)

        return LLMResponse(text="\n".join(text_chunks).strip(), tool_calls=tool_calls)
