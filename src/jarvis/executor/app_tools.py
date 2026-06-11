"""Запуск программ. На Windows используем os.startfile, на других — subprocess."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from jarvis.core.logging_setup import logger
from jarvis.core.types import ToolResult


# Псевдонимы популярных программ Windows (рус + англ)
_WIN_ALIASES: dict[str, str] = {
    "блокнот": "notepad.exe", "notepad": "notepad.exe",
    "калькулятор": "calc.exe", "calculator": "calc.exe", "calc": "calc.exe",
    "проводник": "explorer.exe", "explorer": "explorer.exe",
    "paint": "mspaint.exe", "паинт": "mspaint.exe", "рисование": "mspaint.exe",
    "cmd": "cmd.exe", "командная строка": "cmd.exe",
    "powershell": "powershell.exe", "терминал": "powershell.exe",
    "диспетчер задач": "taskmgr.exe", "диспетчер": "taskmgr.exe",
    "taskmgr": "taskmgr.exe", "task manager": "taskmgr.exe",
    "панель управления": "control.exe", "control panel": "control.exe", "control": "control.exe",
    "параметры": "ms-settings:", "настройки": "ms-settings:", "settings": "ms-settings:",
    "редактор реестра": "regedit.exe", "реестр": "regedit.exe", "regedit": "regedit.exe",
    "службы": "services.msc", "services": "services.msc",
    "диспетчер устройств": "devmgmt.msc", "device manager": "devmgmt.msc",
    "ножницы": "snippingtool.exe", "snipping": "snippingtool.exe",
    "word": "winword.exe", "ворд": "winword.exe",
    "excel": "excel.exe", "эксель": "excel.exe",
}


def open_app(app_name: str) -> ToolResult:
    """Запуск приложения по имени или пути. Честно сообщает, если не найдено."""
    raw = app_name.strip()
    target = _WIN_ALIASES.get(raw.lower(), raw)
    try:
        # 1) Явный путь к файлу/программе
        p = Path(target).expanduser()
        if p.exists():
            if sys.platform == "win32":
                os.startfile(str(p))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(p)])
            else:
                subprocess.Popen(["xdg-open", str(p)])
            return ToolResult.ok(f"Открыто: {p.name}", {"path": str(p)})

        # 2) По имени. На Windows os.startfile ищет exe в PATH/App Paths,
        #    умеет .msc и ms-settings:, и ВЫБРАСЫВАЕТ ошибку, если не найдено
        #    (раньше shell=True «успешно» молчал при несуществующей программе).
        if sys.platform == "win32":
            os.startfile(target)  # type: ignore[attr-defined]
        else:
            subprocess.Popen([target])
        return ToolResult.ok(f"Открыто: {app_name}", {"command": target})

    except (FileNotFoundError, OSError) as e:
        logger.warning(f"open_app: не найдено '{app_name}' ({target}): {e}")
        return ToolResult.fail(
            f"Не удалось найти приложение «{app_name}». "
            f"Уточните название или укажите полный путь к .exe."
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("open_app")
        return ToolResult.fail(f"Не удалось открыть «{app_name}»: {e}")


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
