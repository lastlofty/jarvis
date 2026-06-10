"""Подсистема плагинов Jarvis.

Плагин = папка в каталоге plugins/, которая расширяет агента:
  • скиллами (инструментами, доступными модели) — файл skill.py;
  • знаниями (документами для RAG) — любые .md/.txt и т.п.

Схема "MCP из плагинов из скиллов + RAG": каждый плагин приносит набор скиллов
и/или базу знаний, агент автоматически их подхватывает и учится на них.
"""
from __future__ import annotations

from jarvis.plugins.loader import PluginInfo, load_plugins

__all__ = ["PluginInfo", "load_plugins"]
