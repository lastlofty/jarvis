"""Скилл анализа звонков и заполнения CRM.

Инструменты делают структурную часть (чтение транскрипта, хранение карточек CRM),
а саму выжимку/извлечение полей делает сам агент (LLM) на основе текста.
CRM хранится локально в <SAFE_ROOT>/crm/records.json.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jarvis.core.config import settings
from jarvis.core.docs import read_document
from jarvis.core.types import ToolResult


def _crm_path() -> Path:
    p = Path(settings.safe_root) / "crm"
    p.mkdir(parents=True, exist_ok=True)
    return p / "records.json"


def _load() -> list[dict]:
    f = _crm_path()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def read_transcript(path: str) -> ToolResult:
    """Читает транскрипт звонка (txt/pdf) для анализа."""
    text, err = read_document(path)
    if err:
        return ToolResult.fail(err)
    return ToolResult.ok(text[:6000], {"length": len(text)})


def save_crm_record(
    client: str,
    summary: str,
    action_items: str = "",
    status: str = "новый",
    next_step: str = "",
) -> ToolResult:
    """Сохраняет карточку звонка в CRM."""
    records = _load()
    rec = {
        "id": len(records) + 1,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "client": client,
        "summary": summary,
        "action_items": action_items,
        "status": status,
        "next_step": next_step,
    }
    records.append(rec)
    _crm_path().write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return ToolResult.ok(
        f"Карточка CRM #{rec['id']} сохранена (клиент: {client}, статус: {status}).",
        {"id": rec["id"], "file": str(_crm_path())},
    )


def list_crm_records() -> ToolResult:
    """Возвращает сохранённые карточки CRM."""
    records = _load()
    if not records:
        return ToolResult.ok("В CRM пока нет записей.", {"records": []})
    lines = [f"#{r['id']} {r['client']} — {r['status']}: {r['summary'][:80]}" for r in records]
    return ToolResult.ok("\n".join(lines), {"count": len(records), "records": records})


DECLARATIONS = [
    {
        "name": "read_transcript",
        "description": "Прочитать транскрипт звонка (txt/pdf) для анализа и саммари.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Путь к файлу транскрипта"}},
            "required": ["path"],
        },
    },
    {
        "name": "save_crm_record",
        "description": "Сохранить карточку звонка в CRM после анализа. Заполни client, summary, action_items, status, next_step.",
        "parameters": {
            "type": "object",
            "properties": {
                "client": {"type": "string", "description": "Клиент/компания"},
                "summary": {"type": "string", "description": "Краткое саммари звонка"},
                "action_items": {"type": "string", "description": "Задачи/договорённости"},
                "status": {"type": "string", "description": "Статус сделки (новый/в работе/выиграна/проиграна)"},
                "next_step": {"type": "string", "description": "Следующий шаг"},
            },
            "required": ["client", "summary"],
        },
    },
    {
        "name": "list_crm_records",
        "description": "Показать сохранённые карточки CRM.",
        "parameters": {"type": "object", "properties": {}},
    },
]

HANDLERS = {
    "read_transcript": read_transcript,
    "save_crm_record": save_crm_record,
    "list_crm_records": list_crm_records,
}
