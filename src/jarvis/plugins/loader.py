"""Загрузчик плагинов.

Каждый плагин — подпапка в plugins_dir со структурой:

    plugins/<name>/
        manifest.json      # {name, description, knowledge?: [...], enabled?: true}
        skill.py           # опц.: DECLARATIONS: list, HANDLERS: dict
        *.md / *.txt       # опц.: документы для базы знаний (RAG)

manifest.json минимален: достаточно {"name": "...", "description": "..."}.
Если ключ "knowledge" не задан — индексируются все .md/.txt в папке плагина.
"""
from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger
from jarvis.executor import registry
from jarvis.rag.store import rag


@dataclass
class PluginInfo:
    name: str
    description: str
    path: Path
    skills: list[str] = field(default_factory=list)
    knowledge_files: list[str] = field(default_factory=list)
    error: str | None = None


def _load_skill_module(skill_path: Path, plugin_name: str):
    """Импортирует skill.py из произвольного пути."""
    spec = importlib.util.spec_from_file_location(
        f"jarvis_plugin_{plugin_name}", skill_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"не удалось загрузить spec для {skill_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_one(folder: Path) -> PluginInfo:
    manifest_path = folder / "manifest.json"
    name = folder.name
    description = ""
    knowledge: list[str] | None = None
    enabled = True

    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            name = data.get("name", name)
            description = data.get("description", "")
            knowledge = data.get("knowledge")
            enabled = data.get("enabled", True)
        except (json.JSONDecodeError, OSError) as e:
            return PluginInfo(name, "", folder, error=f"manifest.json: {e}")

    info = PluginInfo(name=name, description=description, path=folder)
    if not enabled:
        info.error = "отключён в manifest.json"
        return info

    # 1) Скиллы (инструменты)
    skill_py = folder / "skill.py"
    if skill_py.exists():
        try:
            module = _load_skill_module(skill_py, name)
            decls = getattr(module, "DECLARATIONS", [])
            handlers = getattr(module, "HANDLERS", {})
            registry.register_many(decls, handlers)
            info.skills = [d["name"] for d in decls]
        except Exception as e:  # noqa: BLE001
            info.error = f"skill.py: {e}"
            logger.exception(f"плагин {name}: ошибка skill.py")

    # 2) Знания (RAG)
    if knowledge is None:
        kb_files = [p for p in folder.rglob("*") if p.suffix.lower() in {".md", ".txt"}]
    else:
        kb_files = [folder / k for k in knowledge]
    for kb in kb_files:
        if kb.exists():
            n = rag.add_file(kb)
            if n:
                info.knowledge_files.append(kb.name)

    return info


def load_plugins(plugins_dir: str | None = None) -> list[PluginInfo]:
    """Загружает все плагины из каталога. Возвращает список с результатами."""
    base = Path(plugins_dir or settings.plugins_dir)
    if not base.exists():
        logger.info(f"Папка плагинов не найдена ({base}) — пропускаю")
        return []

    loaded: list[PluginInfo] = []
    for folder in sorted(base.iterdir()):
        if not folder.is_dir() or folder.name.startswith((".", "_")):
            continue
        info = _load_one(folder)
        loaded.append(info)
        if info.error:
            logger.warning(f"Плагин {info.name}: {info.error}")
        else:
            logger.info(
                f"Плагин загружен: {info.name} "
                f"(скиллов: {len(info.skills)}, знаний: {len(info.knowledge_files)})"
            )
    return loaded
