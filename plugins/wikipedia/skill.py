"""Пример скилла-плагина: поиск кратких справок в Википедии.

Использует бесплатный REST API Википедии (без ключа). Показывает, как плагин
добавляет агенту новый инструмент: достаточно объявить DECLARATIONS и HANDLERS.
"""
from __future__ import annotations

import httpx

from jarvis.core.types import ToolResult


def wikipedia_summary(query: str, lang: str = "ru") -> ToolResult:
    """Возвращает краткую справку из Википедии по запросу."""
    lang = lang if lang in {"ru", "en"} else "ru"
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            # 1) поиск точного заголовка статьи
            search = client.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": 1,
                },
            ).json()
            hits = search.get("query", {}).get("search", [])
            if not hits:
                return ToolResult.fail(f"В Википедии ничего не найдено по запросу: {query}")
            title = hits[0]["title"]

            # 2) краткая выжимка статьи
            summary = client.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
            ).json()
    except httpx.HTTPError as e:
        return ToolResult.fail(f"Ошибка обращения к Википедии: {e}")

    extract = summary.get("extract", "")
    url = summary.get("content_urls", {}).get("desktop", {}).get("page", "")
    return ToolResult.ok(
        f"{title}\n\n{extract}",
        {"title": title, "extract": extract, "url": url},
    )


DECLARATIONS = [
    {
        "name": "wikipedia_summary",
        "description": "Получить краткую справку из Википедии по теме. Используй для фактов, определений, биографий.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Тема или вопрос"},
                "lang": {"type": "string", "enum": ["ru", "en"], "description": "Язык (ru/en)"},
            },
            "required": ["query"],
        },
    }
]

HANDLERS = {"wikipedia_summary": wikipedia_summary}
