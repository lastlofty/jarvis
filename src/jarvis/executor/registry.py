"""Реестр инструментов: схемы для LLM + диспетчер вызовов.

Gemini-формат function declarations:
https://ai.google.dev/gemini-api/docs/function-calling
"""
from __future__ import annotations

import asyncio
import inspect
from typing import Any, Awaitable, Callable

from jarvis.core.logging_setup import logger
from jarvis.core.types import ToolResult
from jarvis.executor import app_tools, comm_tools, file_tools, input_tools
from jarvis.memory.db import db


# Тип обработчика: либо обычная функция, либо корутина.
ToolFn = Callable[..., ToolResult] | Callable[..., Awaitable[ToolResult]]


# Декларации инструментов в формате Gemini (упрощённо OpenAPI).
TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "create_folder",
        "description": "Создаёт папку. path — родительская директория (можно '.'), folder_name — имя новой папки.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Родительская папка"},
                "folder_name": {"type": "string", "description": "Имя новой папки"},
            },
            "required": ["path", "folder_name"],
        },
    },
    {
        "name": "create_file",
        "description": "Создаёт текстовый файл с содержимым.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "delete_file",
        "description": (
            "Удаляет файл или папку. ВНИМАНИЕ: сначала ОБЯЗАТЕЛЬНО спросите подтверждение "
            "через ask_user, затем вызовите с confirmed=true."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "confirmed": {
                    "type": "boolean",
                    "description": "Только true после подтверждения пользователем",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "move_file",
        "description": "Перемещает файл/папку.",
        "parameters": {
            "type": "object",
            "properties": {
                "src": {"type": "string"},
                "dst": {"type": "string"},
            },
            "required": ["src", "dst"],
        },
    },
    {
        "name": "list_directory",
        "description": "Возвращает содержимое папки.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "click",
        "description": "Кликнуть мышью в координатах (x, y).",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "button": {"type": "string", "enum": ["left", "right", "middle"]},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "write_text",
        "description": "Печатает текст с клавиатуры.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "press_hotkey",
        "description": "Нажимает комбинацию клавиш, например 'ctrl+c', 'win+d'.",
        "parameters": {
            "type": "object",
            "properties": {"combination": {"type": "string"}},
            "required": ["combination"],
        },
    },
    {
        "name": "get_mouse_position",
        "description": "Возвращает текущие координаты курсора.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "take_screenshot",
        "description": "Делает скриншот рабочего стола и возвращает путь к файлу.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "open_app",
        "description": "Запускает приложение по имени ('блокнот', 'калькулятор') или пути к exe.",
        "parameters": {
            "type": "object",
            "properties": {"app_name": {"type": "string"}},
            "required": ["app_name"],
        },
    },
    {
        "name": "run_script",
        "description": "Запускает скрипт (.py / .bat / .ps1 / .sh).",
        "parameters": {
            "type": "object",
            "properties": {"script_path": {"type": "string"}},
            "required": ["script_path"],
        },
    },
    {
        "name": "ask_user",
        "description": (
            "Задать пользователю уточняющий вопрос (например, подтверждение удаления). "
            "Возвращает текст ответа. ИСПОЛЬЗУЙТЕ перед удалением файлов."
        ),
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    },
    {
        "name": "send_notification",
        "description": "Отправляет уведомление на мобильное приложение.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["title", "message"],
        },
    },
    {
        "name": "collect_app_usage",
        "description": (
            "Возвращает статистику времени использования приложений за период. "
            "Даты в формате YYYY-MM-DD. По умолчанию — последние 24 часа."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
            },
        },
    },
    {
        "name": "generate_report",
        "description": "Создаёт отчёт. format: 'text' | 'csv' | 'pdf'.",
        "parameters": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["text", "csv", "pdf"]},
            },
        },
    },
    {
        "name": "get_active_window",
        "description": "Возвращает заголовок и имя процесса активного окна.",
        "parameters": {"type": "object", "properties": {}},
    },
]


# ---------- Реальный диспетчер ----------


def _get_active_window_tool() -> ToolResult:
    from jarvis.observer.observer import observer

    return ToolResult.ok(
        "Активное окно",
        {
            "title": observer.get_active_window_title(),
            "process": observer.get_foreground_process(),
        },
    )


HANDLERS: dict[str, ToolFn] = {
    "create_folder": file_tools.create_folder,
    "create_file": file_tools.create_file,
    "delete_file": file_tools.delete_file,
    "move_file": file_tools.move_file,
    "list_directory": file_tools.list_directory,
    "click": input_tools.click,
    "write_text": input_tools.write_text,
    "press_hotkey": input_tools.press_hotkey,
    "get_mouse_position": input_tools.get_mouse_position,
    "take_screenshot": input_tools.take_screenshot,
    "open_app": app_tools.open_app,
    "run_script": app_tools.run_script,
    "ask_user": comm_tools.ask_user,
    "send_notification": comm_tools.send_notification,
    "collect_app_usage": comm_tools.collect_app_usage,
    "generate_report": comm_tools.generate_report,
    "get_active_window": _get_active_window_tool,
}


# ---------- Динамическая регистрация (RAG / плагины / MCP) ----------

# Декларации и обработчики, добавленные во время выполнения.
_EXTRA_DECLARATIONS: list[dict[str, Any]] = []
_EXTRA_HANDLERS: dict[str, ToolFn] = {}


def register_tool(declaration: dict[str, Any], handler: ToolFn) -> None:
    """Регистрирует новый инструмент (из RAG, плагина или MCP).

    Повторная регистрация с тем же именем перезаписывает обработчик.
    """
    name = declaration["name"]
    _EXTRA_HANDLERS[name] = handler
    _EXTRA_DECLARATIONS[:] = [d for d in _EXTRA_DECLARATIONS if d["name"] != name]
    _EXTRA_DECLARATIONS.append(declaration)
    logger.info(f"Зарегистрирован инструмент: {name}")


def register_many(declarations: list[dict[str, Any]], handlers: dict[str, ToolFn]) -> None:
    """Пакетная регистрация (декларации + соответствующие обработчики)."""
    for decl in declarations:
        h = handlers.get(decl["name"])
        if h is not None:
            register_tool(decl, h)


def all_declarations() -> list[dict[str, Any]]:
    """Все доступные сейчас декларации: базовые + динамические."""
    return TOOL_DECLARATIONS + _EXTRA_DECLARATIONS


# Встроенные RAG-инструменты и инструменты памяти регистрируем сразу.
from jarvis.executor import rag_tools  # noqa: E402

register_many(rag_tools.RAG_DECLARATIONS, rag_tools.RAG_HANDLERS)

from jarvis.executor import memory_tools  # noqa: E402

register_many(memory_tools.MEMORY_DECLARATIONS, memory_tools.MEMORY_HANDLERS)

from jarvis.executor import plan_tools  # noqa: E402

register_many(plan_tools.PLAN_DECLARATIONS, plan_tools.PLAN_HANDLERS)


async def dispatch(name: str, arguments: dict[str, Any]) -> ToolResult:
    """Безопасно вызывает инструмент по имени и логирует результат."""
    fn = HANDLERS.get(name) or _EXTRA_HANDLERS.get(name)
    if fn is None:
        result = ToolResult.fail(f"Неизвестный инструмент: {name}")
        db.log_action(name, arguments, result.to_dict(), error=result.message)
        return result

    try:
        if inspect.iscoroutinefunction(fn):
            result = await fn(**arguments)  # type: ignore[arg-type]
        else:
            result = await asyncio.to_thread(fn, **arguments)  # type: ignore[arg-type]

        db.log_action(name, arguments, result.to_dict(),
                      error=None if result.status == "success" else result.message)
        logger.info(f"tool {name} -> {result.status}: {result.message}")
        return result
    except TypeError as e:
        # Например, не хватает аргумента — частая проблема LLM
        result = ToolResult.fail(f"Неверные аргументы для {name}: {e}")
        db.log_action(name, arguments, result.to_dict(), error=str(e))
        return result
    except Exception as e:
        logger.exception(f"tool {name} crashed")
        result = ToolResult.fail(f"Внутренняя ошибка {name}: {e}")
        db.log_action(name, arguments, result.to_dict(), error=str(e))
        return result
