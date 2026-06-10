"""Инструменты RAG для агента: поиск и индексация базы знаний."""
from __future__ import annotations

from jarvis.core.types import ToolResult
from jarvis.rag.store import rag


def rag_search(query: str, k: int = 3) -> ToolResult:
    """Ищет релевантные фрагменты в базе знаний."""
    hits = rag.search(query, k=k)
    if not hits:
        return ToolResult.ok("В базе знаний ничего не найдено.", {"hits": []})
    data = [{"source": h.source, "text": h.text, "score": round(h.score, 3)} for h in hits]
    preview = "\n\n".join(f"• {h.source}\n{h.text[:200]}" for h in hits)
    return ToolResult.ok(f"Найдено фрагментов: {len(hits)}\n{preview}", {"hits": data})


def rag_index(path: str) -> ToolResult:
    """Индексирует файл или папку в базу знаний."""
    from pathlib import Path

    p = Path(path)
    if p.is_dir():
        results = rag.index_folder(p)
        return ToolResult.ok(
            f"Проиндексировано файлов: {len(results)}", {"files": results, **rag.stats()}
        )
    if p.is_file():
        n = rag.add_file(p)
        return ToolResult.ok(f"Проиндексирован файл, чанков: {n}", rag.stats())
    return ToolResult.fail(f"Путь не найден: {path}")


def rag_stats() -> ToolResult:
    """Показывает статистику базы знаний."""
    s = rag.stats()
    return ToolResult.ok(
        f"База знаний: {s['chunks']} чанков из {s['sources']} источников.", s
    )


RAG_DECLARATIONS = [
    {
        "name": "rag_search",
        "description": "Поиск по базе знаний (RAG). Используй, когда вопрос про документы/факты, которые могли быть проиндексированы.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос"},
                "k": {"type": "integer", "description": "Сколько фрагментов вернуть (по умолч. 3)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "rag_index",
        "description": "Добавить файл или папку в базу знаний (RAG), чтобы потом искать по ним.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Путь к файлу или папке"}},
            "required": ["path"],
        },
    },
    {
        "name": "rag_stats",
        "description": "Статистика базы знаний: сколько фрагментов и источников проиндексировано.",
        "parameters": {"type": "object", "properties": {}},
    },
]

RAG_HANDLERS = {
    "rag_search": rag_search,
    "rag_index": rag_index,
    "rag_stats": rag_stats,
}
