"""Инструменты долговременной памяти: запомнить и вспомнить."""
from __future__ import annotations

from jarvis.core.types import ToolResult
from jarvis.memory.long_term import long_term


def remember(fact: str) -> ToolResult:
    """Сохраняет факт в долговременную память."""
    total = long_term.remember(fact)
    return ToolResult.ok(f"Запомнил. Всего воспоминаний: {total}.", {"count": total})


def recall(query: str) -> ToolResult:
    """Ищет релевантные воспоминания."""
    hits = long_term.recall(query)
    if not hits:
        return ToolResult.ok("В памяти ничего подходящего не нашлось.", {"hits": []})
    text = "\n".join(f"• {h.text}" for h in hits)
    return ToolResult.ok(f"Вспомнил:\n{text}", {"hits": [h.text for h in hits]})


MEMORY_DECLARATIONS = [
    {
        "name": "remember",
        "description": "Сохранить важный факт о пользователе или контексте в долговременную память (между сессиями). Используй, когда пользователь сообщает предпочтения, имена, факты о себе.",
        "parameters": {
            "type": "object",
            "properties": {"fact": {"type": "string", "description": "Факт для запоминания"}},
            "required": ["fact"],
        },
    },
    {
        "name": "recall",
        "description": "Вспомнить ранее сохранённые факты по теме из долговременной памяти.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "О чём вспомнить"}},
            "required": ["query"],
        },
    },
]

MEMORY_HANDLERS = {"remember": remember, "recall": recall}
