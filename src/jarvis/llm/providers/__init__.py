"""Фабрика провайдеров LLM.

Выбор модели делается по имени: "glm" (по умолчанию), "gemini", "ollama".
Импорт конкретного SDK ленивый — чтобы отсутствие, например, google-generativeai
не ломало запуск с GLM/Ollama.
"""
from __future__ import annotations

from jarvis.core.config import settings
from jarvis.llm.providers.base import LLMProvider, LLMResponse, Message, ToolCall

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "Message",
    "ToolCall",
    "get_provider",
    "AVAILABLE_PROVIDERS",
]

AVAILABLE_PROVIDERS = ("glm", "gemini", "ollama")


def get_provider(name: str | None = None) -> LLMProvider:
    """Создаёт провайдера по имени (или из настроек)."""
    name = (name or settings.llm_provider or "glm").lower().strip()

    if name == "glm":
        from jarvis.llm.providers.glm import GLMProvider

        return GLMProvider()
    if name == "gemini":
        from jarvis.llm.providers.gemini import GeminiProvider

        return GeminiProvider()
    if name == "ollama":
        from jarvis.llm.providers.ollama_provider import OllamaProvider

        return OllamaProvider()

    raise ValueError(
        f"Неизвестный провайдер LLM: {name!r}. Доступны: {', '.join(AVAILABLE_PROVIDERS)}"
    )
