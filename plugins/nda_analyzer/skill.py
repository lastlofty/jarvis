"""Скилл анализа NDA/договоров и маршрутизации документов.

Агент читает документ, анализирует ключевые пункты (стороны, срок, предмет,
конфиденциальность, ответственность, право), затем маршрутизирует файл в папку
категории. Всё в пределах SAFE_ROOT.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from jarvis.core.config import settings
from jarvis.core.docs import read_document
from jarvis.core.types import ToolResult
from jarvis.executor.safety import UnsafePathError, resolve_safe


def read_nda(path: str) -> ToolResult:
    """Читает текст документа (txt/pdf) для анализа."""
    text, err = read_document(path)
    if err:
        return ToolResult.fail(err)
    return ToolResult.ok(text[:8000], {"length": len(text)})


def route_document(path: str, category: str) -> ToolResult:
    """Перемещает документ в папку категории (<SAFE_ROOT>/documents/<category>)."""
    try:
        src = resolve_safe(path)
    except UnsafePathError:
        return ToolResult.fail("Исходный файл вне безопасной зоны (SAFE_ROOT).")
    if not src.exists():
        return ToolResult.fail(f"Файл не найден: {src}")

    safe_cat = "".join(c for c in category if c.isalnum() or c in " _-")[:50].strip() or "прочее"
    dst_dir = Path(settings.safe_root) / "documents" / safe_cat
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    try:
        shutil.move(str(src), str(dst))
    except OSError as e:
        return ToolResult.fail(f"Не удалось переместить: {e}")
    return ToolResult.ok(
        f"Документ перемещён в категорию «{safe_cat}»: {dst}", {"path": str(dst)}
    )


DECLARATIONS = [
    {
        "name": "read_nda",
        "description": "Прочитать документ/NDA (txt/pdf) для анализа ключевых условий.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Путь к документу"}},
            "required": ["path"],
        },
    },
    {
        "name": "route_document",
        "description": "Маршрутизировать (переместить) документ в папку категории после анализа: например 'NDA', 'договоры', 'на подпись', 'отклонённые'.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Путь к документу"},
                "category": {"type": "string", "description": "Категория/папка назначения"},
            },
            "required": ["path", "category"],
        },
    },
]

HANDLERS = {"read_nda": read_nda, "route_document": route_document}
