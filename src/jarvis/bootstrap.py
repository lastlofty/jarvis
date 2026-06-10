"""Инициализация расширений агента: плагины (скиллы + знания) и MCP.

Вызывается один раз при старте любого режима (консоль / GUI / сервер).
Синхронная часть (плагины, RAG) и асинхронная (MCP) разделены, потому что
MCP-сессии должны подниматься внутри активного event-loop.
"""
from __future__ import annotations

from jarvis.core.logging_setup import logger
from jarvis.plugins import load_plugins

_plugins_loaded = False


def load_extensions() -> None:
    """Синхронная инициализация: загрузка плагинов и их знаний в RAG."""
    global _plugins_loaded
    if _plugins_loaded:
        return
    plugins = load_plugins()
    total_skills = sum(len(p.skills) for p in plugins)
    total_kb = sum(len(p.knowledge_files) for p in plugins)
    logger.info(
        f"Расширения: плагинов {len(plugins)}, скиллов {total_skills}, "
        f"файлов знаний {total_kb}"
    )
    _plugins_loaded = True


async def start_mcp() -> None:
    """Асинхронная инициализация MCP-серверов (если включены)."""
    from jarvis.mcp import mcp_manager

    await mcp_manager.start()


async def stop_mcp() -> None:
    from jarvis.mcp import mcp_manager

    await mcp_manager.stop()
