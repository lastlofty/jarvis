"""Общие фикстуры pytest. Изолируем БД и SAFE_ROOT в tmp_path."""
from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Каждый тест получает изолированную SAFE_ROOT и БД."""
    safe = tmp_path / "safe"
    safe.mkdir()
    db = tmp_path / "db" / "test.db"
    db.parent.mkdir()

    monkeypatch.setenv("SAFE_ROOT", str(safe))
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("ENABLE_OBSERVER", "false")
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "log.log"))
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-tests")
    monkeypatch.setenv("AUTH_TOKEN", "test-token")

    # Сбрасываем кэшированные singletons модулей jarvis
    import importlib
    import sys

    for mod in list(sys.modules):
        if mod.startswith("jarvis"):
            sys.modules.pop(mod, None)

    yield
