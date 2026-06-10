"""Юнит-тесты слоя БД."""
from __future__ import annotations

import time
from datetime import datetime, timedelta


def test_open_close_session_records_duration():
    from jarvis.memory.db import db

    sid = db.open_session("chrome.exe", "Google")
    time.sleep(0.05)
    db.close_session(sid)

    rows = db.query_app_usage(
        datetime.utcnow() - timedelta(minutes=1), datetime.utcnow() + timedelta(minutes=1)
    )
    chrome = [r for r in rows if r["app_name"] == "chrome.exe"]
    assert chrome, "Chrome row missing"
    assert chrome[0]["total_s"] >= 0


def test_log_action_persists():
    import sqlite3
    from jarvis.core.config import settings
    from jarvis.memory.db import db

    db.log_action("create_folder", {"folder_name": "x"}, {"status": "success"}, None)

    cx = sqlite3.connect(settings.db_path)
    rows = cx.execute("SELECT action_name FROM action_log").fetchall()
    cx.close()
    assert any(r[0] == "create_folder" for r in rows)


def test_query_app_usage_aggregates():
    from jarvis.memory.db import db

    sid1 = db.open_session("notepad.exe", "Untitled")
    db.close_session(sid1)
    sid2 = db.open_session("notepad.exe", "file.txt")
    db.close_session(sid2)

    rows = db.query_app_usage(
        datetime.utcnow() - timedelta(minutes=1),
        datetime.utcnow() + timedelta(minutes=1),
    )
    notepad = [r for r in rows if r["app_name"] == "notepad.exe"]
    assert notepad
    assert notepad[0]["sessions"] >= 2
