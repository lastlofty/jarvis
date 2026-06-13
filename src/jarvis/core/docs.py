"""Чтение документов (txt/md/csv/json/pdf) в пределах SAFE_ROOT.

Используется бизнес-плагинами (анализ звонков, NDA, счета). PDF читается через
pypdf (если установлен). Возвращает (текст, ошибка).
"""
from __future__ import annotations

from pathlib import Path

from jarvis.executor.safety import UnsafePathError, resolve_safe

_TEXT_SUFFIXES = {".txt", ".md", ".csv", ".log", ".json", ".rst", ""}


def read_document(path: str) -> tuple[str | None, str | None]:
    """Читает документ. Возвращает (text, None) или (None, error)."""
    try:
        p = resolve_safe(path)
    except UnsafePathError:
        return None, "Файл вне безопасной зоны (SAFE_ROOT). Переместите его в рабочую папку."
    if not p.exists():
        return None, f"Файл не найден: {p}"

    suffix = p.suffix.lower()
    if suffix == ".pdf":
        try:
            import pypdf
        except ImportError:
            return None, "Для чтения PDF установите пакет: pip install pypdf"
        try:
            reader = pypdf.PdfReader(str(p))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            return (text.strip() or "(PDF без извлекаемого текста — возможно, скан)"), None
        except Exception as e:  # noqa: BLE001
            return None, f"Ошибка чтения PDF: {e}"

    if suffix in _TEXT_SUFFIXES:
        try:
            return p.read_text(encoding="utf-8", errors="ignore"), None
        except OSError as e:
            return None, f"Ошибка чтения файла: {e}"

    return None, f"Неподдерживаемый формат: {suffix} (поддерживаются txt, md, csv, json, pdf)"
