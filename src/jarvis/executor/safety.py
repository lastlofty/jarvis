"""Проверка, что путь не выходит за пределы SAFE_ROOT.

Защита от случайного "rm -rf /" и от LLM, перепутавшей слэши.
"""
from __future__ import annotations

from pathlib import Path

from jarvis.core.config import settings


class UnsafePathError(Exception):
    """Запрошенный путь выходит за пределы безопасной зоны."""


def resolve_safe(path: str | Path) -> Path:
    """Превращает строку в абсолютный Path и проверяет, что он внутри safe_root.

    Если путь относительный — он считается относительно safe_root.
    """
    safe_root = Path(settings.safe_root).expanduser().resolve()
    raw = Path(path).expanduser()
    full = (safe_root / raw if not raw.is_absolute() else raw).resolve()

    try:
        full.relative_to(safe_root)
    except ValueError as e:
        raise UnsafePathError(
            f"Путь {full} вне безопасной зоны {safe_root}. "
            f"Измените SAFE_ROOT в .env или используйте относительный путь."
        ) from e
    return full
