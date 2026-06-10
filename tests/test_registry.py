"""Тест реестра инструментов: dispatch вызывает нужный handler и логирует."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_returns_error():
    from jarvis.executor.registry import dispatch

    result = await dispatch("nonexistent_tool", {})
    assert result.status == "error"
    assert "Неизвестный" in result.message


@pytest.mark.asyncio
async def test_dispatch_create_folder_via_registry():
    from pathlib import Path

    from jarvis.core.config import settings
    from jarvis.executor.registry import dispatch

    result = await dispatch("create_folder", {"path": ".", "folder_name": "via_registry"})
    assert result.status == "success"
    assert (Path(settings.safe_root) / "via_registry").is_dir()


@pytest.mark.asyncio
async def test_dispatch_logs_to_db():
    import sqlite3

    from jarvis.core.config import settings
    from jarvis.executor.registry import dispatch

    await dispatch("create_folder", {"path": ".", "folder_name": "logged"})

    cx = sqlite3.connect(settings.db_path)
    rows = cx.execute("SELECT action_name FROM action_log").fetchall()
    cx.close()
    assert any(r[0] == "create_folder" for r in rows)


@pytest.mark.asyncio
async def test_dispatch_bad_args_returns_error_not_exception():
    """Если LLM передала плохие аргументы — это error, а не падение сервера."""
    from jarvis.executor.registry import dispatch

    result = await dispatch("create_folder", {"wrong_arg": "x"})
    assert result.status == "error"
