"""Файловые операции, безопасные относительно SAFE_ROOT."""
from __future__ import annotations

import shutil
from pathlib import Path

from jarvis.core.logging_setup import logger
from jarvis.core.types import ToolResult
from jarvis.executor.safety import UnsafePathError, resolve_safe


def create_folder(path: str, folder_name: str) -> ToolResult:
    """Создаёт папку folder_name внутри path. Если path пустой — внутри SAFE_ROOT."""
    try:
        base = resolve_safe(path or ".")
        target = (base / folder_name).resolve()
        # повторно валидируем — на случай ".." в folder_name
        resolve_safe(target)
        target.mkdir(parents=True, exist_ok=True)
        return ToolResult.ok(f"Папка создана: {target}", {"path": str(target)})
    except UnsafePathError as e:
        return ToolResult.fail(str(e))
    except Exception as e:
        logger.exception("create_folder")
        return ToolResult.fail(f"Не удалось создать папку: {e}")


def create_file(path: str, content: str = "") -> ToolResult:
    try:
        target = resolve_safe(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult.ok(f"Файл создан: {target}", {"path": str(target)})
    except UnsafePathError as e:
        return ToolResult.fail(str(e))
    except Exception as e:
        logger.exception("create_file")
        return ToolResult.fail(f"Не удалось создать файл: {e}")


def delete_file(path: str, confirmed: bool = False) -> ToolResult:
    """Удаление требует флага confirmed=True (агент должен спросить через ask_user)."""
    try:
        target = resolve_safe(path)
        if not target.exists():
            return ToolResult.fail(f"Не найдено: {target}")
        if not confirmed:
            return ToolResult.fail(
                "Подтверждение не получено. Спросите пользователя через ask_user "
                "и вызовите снова с confirmed=true."
            )
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return ToolResult.ok(f"Удалено: {target}")
    except UnsafePathError as e:
        return ToolResult.fail(str(e))
    except Exception as e:
        logger.exception("delete_file")
        return ToolResult.fail(f"Ошибка удаления: {e}")


def move_file(src: str, dst: str) -> ToolResult:
    try:
        src_p = resolve_safe(src)
        dst_p = resolve_safe(dst)
        if not src_p.exists():
            return ToolResult.fail(f"Источник не найден: {src_p}")
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_p), str(dst_p))
        return ToolResult.ok(f"Перемещено: {src_p} -> {dst_p}")
    except UnsafePathError as e:
        return ToolResult.fail(str(e))
    except Exception as e:
        logger.exception("move_file")
        return ToolResult.fail(f"Ошибка перемещения: {e}")


def list_directory(path: str = ".") -> ToolResult:
    try:
        target = resolve_safe(path)
        if not target.is_dir():
            return ToolResult.fail(f"Не папка: {target}")
        items = []
        for child in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name)):
            items.append(
                {
                    "name": child.name,
                    "type": "dir" if child.is_dir() else "file",
                    "size": child.stat().st_size if child.is_file() else None,
                }
            )
        return ToolResult.ok(
            f"Содержимое {target} ({len(items)} элементов)",
            {"path": str(target), "items": items},
        )
    except UnsafePathError as e:
        return ToolResult.fail(str(e))
    except Exception as e:
        logger.exception("list_directory")
        return ToolResult.fail(f"Ошибка чтения папки: {e}")
