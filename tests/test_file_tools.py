"""Юнит-тесты файловых операций и safety guard."""
from __future__ import annotations

from pathlib import Path


def test_create_folder_inside_safe_root():
    from jarvis.core.config import settings
    from jarvis.executor.file_tools import create_folder

    res = create_folder(".", "myproject")
    assert res.status == "success"
    assert (Path(settings.safe_root) / "myproject").is_dir()


def test_create_file_writes_content():
    from jarvis.core.config import settings
    from jarvis.executor.file_tools import create_file

    res = create_file("hello.txt", content="привет")
    assert res.status == "success"
    target = Path(settings.safe_root) / "hello.txt"
    assert target.read_text(encoding="utf-8") == "привет"


def test_delete_requires_confirmation():
    from jarvis.executor.file_tools import create_file, delete_file

    create_file("victim.txt", "x")
    res = delete_file("victim.txt", confirmed=False)
    assert res.status == "error"
    assert "одтвержд" in res.message  # "подтверждение"

    res2 = delete_file("victim.txt", confirmed=True)
    assert res2.status == "success"


def test_path_outside_safe_root_rejected():
    """Безопасность: попытка выйти за SAFE_ROOT через .. должна провалиться."""
    from jarvis.executor.file_tools import create_file

    res = create_file("../outside.txt", "evil")
    assert res.status == "error"
    assert "вне безопасной зоны" in res.message.lower() or "outside" in res.message.lower() or "безопас" in res.message.lower()


def test_list_directory():
    from jarvis.executor.file_tools import create_file, list_directory

    create_file("a.txt", "1")
    create_file("b.txt", "2")
    res = list_directory(".")
    assert res.status == "success"
    names = {item["name"] for item in res.data["items"]}
    assert {"a.txt", "b.txt"} <= names


def test_move_file():
    from jarvis.core.config import settings
    from jarvis.executor.file_tools import create_file, move_file

    create_file("src.txt", "data")
    res = move_file("src.txt", "moved.txt")
    assert res.status == "success"
    assert (Path(settings.safe_root) / "moved.txt").exists()
    assert not (Path(settings.safe_root) / "src.txt").exists()
