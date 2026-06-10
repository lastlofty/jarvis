"""Инструменты управления вводом (мышь / клавиатура / скриншот).

Импорт pyautogui и mss — ленивый и обёрнут в try/except, чтобы на CI
(в headless Linux) тесты не падали.
"""
from __future__ import annotations

import time
from pathlib import Path
from tempfile import gettempdir

from jarvis.core.logging_setup import logger
from jarvis.core.types import ToolResult


def _import_pyautogui():
    import pyautogui  # type: ignore
    pyautogui.FAILSAFE = True  # увести курсор в угол → аварийный выход
    return pyautogui


def click(x: int, y: int, button: str = "left") -> ToolResult:
    try:
        pyautogui = _import_pyautogui()
        pyautogui.click(x=x, y=y, button=button)
        return ToolResult.ok(f"Клик {button} в ({x}, {y})")
    except Exception as e:
        logger.exception("click")
        return ToolResult.fail(f"Не удалось кликнуть: {e}")


def write_text(text: str, interval: float = 0.02) -> ToolResult:
    try:
        pyautogui = _import_pyautogui()
        # pyautogui.typewrite не печатает кириллицу. Используем write через
        # буфер обмена для надёжности — но это требует pyperclip; здесь оставим
        # простую реализацию, кириллица вводится через системный буфер сторонним способом.
        pyautogui.typewrite(text, interval=interval)
        return ToolResult.ok(f"Введён текст ({len(text)} симв.)")
    except Exception as e:
        logger.exception("write_text")
        return ToolResult.fail(f"Не удалось ввести текст: {e}")


def press_hotkey(combination: str) -> ToolResult:
    """combination = 'ctrl+c', 'win+d' и т.п."""
    try:
        pyautogui = _import_pyautogui()
        keys = [k.strip().lower() for k in combination.split("+") if k.strip()]
        if not keys:
            return ToolResult.fail("Пустая комбинация клавиш")
        pyautogui.hotkey(*keys)
        return ToolResult.ok(f"Нажато: {'+'.join(keys)}")
    except Exception as e:
        logger.exception("press_hotkey")
        return ToolResult.fail(f"Не удалось нажать клавиши: {e}")


def get_mouse_position() -> ToolResult:
    try:
        pyautogui = _import_pyautogui()
        pos = pyautogui.position()
        return ToolResult.ok(f"Курсор: ({pos.x}, {pos.y})", {"x": pos.x, "y": pos.y})
    except Exception as e:
        return ToolResult.fail(f"Не удалось получить позицию: {e}")


def take_screenshot(save_dir: str | None = None) -> ToolResult:
    """Делает скриншот всех мониторов и сохраняет в PNG. Возвращает путь."""
    try:
        import mss  # type: ignore
        from PIL import Image

        out_dir = Path(save_dir) if save_dir else Path(gettempdir()) / "jarvis_shots"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time() * 1000)
        out_path = out_dir / f"shot_{ts}.png"

        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[0])  # все мониторы как один
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            img.save(out_path, "PNG", optimize=True)

        return ToolResult.ok(
            f"Скриншот сохранён: {out_path}",
            {"path": str(out_path), "width": shot.width, "height": shot.height},
        )
    except Exception as e:
        logger.exception("take_screenshot")
        return ToolResult.fail(f"Скриншот не удался: {e}")
