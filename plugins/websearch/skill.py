"""Скилл поиска в интернете через DuckDuckGo (бесплатно, без ключа).

Использует пакет `ddgs` (или старый `duckduckgo_search`). Если он не установлен —
возвращает понятную подсказку, не ломая агента.
"""
from __future__ import annotations

from jarvis.core.types import ToolResult


def _get_ddgs():
    try:
        from ddgs import DDGS  # новый пакет

        return DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # старое имя

            return DDGS
        except ImportError:
            return None


def web_search(query: str, max_results: int = 5) -> ToolResult:
    """Ищет в интернете и возвращает заголовки, ссылки и сниппеты."""
    DDGS = _get_ddgs()
    if DDGS is None:
        return ToolResult.fail(
            "Веб-поиск недоступен: установите пакет — pip install ddgs"
        )
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:  # noqa: BLE001
        return ToolResult.fail(f"Ошибка поиска: {e}")

    if not results:
        return ToolResult.ok("Ничего не найдено.", {"results": []})

    lines = []
    data = []
    for r in results:
        title = r.get("title", "")
        href = r.get("href") or r.get("url", "")
        body = r.get("body", "")
        lines.append(f"• {title}\n  {href}\n  {body[:160]}")
        data.append({"title": title, "url": href, "snippet": body})
    return ToolResult.ok("\n\n".join(lines), {"results": data})


DECLARATIONS = [
    {
        "name": "web_search",
        "description": "Поиск актуальной информации в интернете (DuckDuckGo). Используй для свежих новостей, цен, фактов, которых нет в базе знаний.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос"},
                "max_results": {"type": "integer", "description": "Сколько результатов (по умолч. 5)"},
            },
            "required": ["query"],
        },
    }
]

HANDLERS = {"web_search": web_search}
