"""Запуск программ. На Windows используем os.startfile, на других — subprocess."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from jarvis.core.logging_setup import logger
from jarvis.core.types import ToolResult


# Удобные псевдонимы для популярных программ Windows
_WIN_ALIASES: dict[str, str] = {
    "блокнот": "notepad.exe",
    "notepad": "notepad.exe",
    "калькулятор": "calc.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "проводник": "explorer.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
}


def open_app(app_name: str) -> ToolResult:
    """Запуск приложения по имени или абсолютному пути."""
    try:
        target = _WIN_ALIASES.get(app_name.strip().lower(), app_name)

        # Если это путь к файлу — запускаем напрямую
        p = Path(target).expanduser()
        if p.exists():
            if sys.platform == "win32":
                os.startfile(str(p))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p)])
            return ToolResult.ok(f"Запущено: {p}", {"path": str(p)})

        # Иначе считаем, что это имя в PATH
        subprocess.Popen(target, shell=(sys.platform == "win32"))
        return ToolResult.ok(f"Запущено: {target}", {"command": target})
    except Exception as e:
        logger.exception("open_app")
        return ToolResult.fail(f"Не удалось запустить '{app_name}': {e}")


def run_script(script_path: str) -> ToolResult:
    """Запуск .py / .bat / .ps1 / .sh скрипта (только в пределах SAFE_ROOT)."""
    from jarvis.executor.safety import UnsafePathError, resolve_safe

    try:
        # Запускать можно только скрипты внутри безопасной зоны —
        # защита от удалённого запуска произвольных системных скриптов.
        try:
            p = resolve_safe(script_path)
        except UnsafePathError:
            return ToolResult.fail(
                "Запуск скрипта вне безопасной зоны (SAFE_ROOT) запрещён."
            )
        if not p.exists():
            return ToolResult.fail(f"Скрипт не найден: {p}")
        if p.suffix == ".py":
            subprocess.Popen([sys.executable, str(p)])
        elif p.suffix in {".bat", ".cmd"}:
            subprocess.Popen([str(p)], shell=True)
        elif p.suffix == ".ps1":
            subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(p)]
            )
        else:
            if sys.platform == "win32":
                os.startfile(str(p))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["bash", str(p)])
        return ToolResult.ok(f"Скрипт запущен: {p}")
    except Exception as e:
        logger.exception("run_script")
        return ToolResult.fail(f"Ошибка запуска: {e}")
