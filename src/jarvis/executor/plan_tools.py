"""Инструменты автономного планирования.

Для сложных многошаговых задач агент сначала строит план (create_plan),
затем выполняет шаги обычными инструментами и отмечает прогресс
(complete_step). Текущий план можно посмотреть (get_plan).

Состояние плана глобальное (на текущую сессию) и может отображаться в GUI
через колбэк on_plan_changed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from jarvis.core.types import ToolResult


@dataclass
class _Step:
    text: str
    done: bool = False


@dataclass
class _Plan:
    steps: list[_Step] = field(default_factory=list)


_plan = _Plan()
# колбэк для GUI: получает список (text, done)
on_plan_changed: Callable[[list[tuple[str, bool]]], None] | None = None


def _notify() -> None:
    if on_plan_changed is not None:
        try:
            on_plan_changed([(s.text, s.done) for s in _plan.steps])
        except Exception:  # noqa: BLE001
            pass


def _render() -> str:
    if not _plan.steps:
        return "План пуст."
    lines = []
    for i, s in enumerate(_plan.steps, 1):
        mark = "[x]" if s.done else "[ ]"
        lines.append(f"{mark} {i}. {s.text}")
    done = sum(1 for s in _plan.steps if s.done)
    return f"План ({done}/{len(_plan.steps)}):\n" + "\n".join(lines)


def create_plan(steps: list[str]) -> ToolResult:
    """Создаёт план из списка шагов."""
    _plan.steps = [_Step(text=str(s)) for s in steps if str(s).strip()]
    _notify()
    return ToolResult.ok(_render(), {"total": len(_plan.steps)})


def complete_step(index: int) -> ToolResult:
    """Отмечает шаг (номер с 1) выполненным."""
    i = int(index) - 1
    if i < 0 or i >= len(_plan.steps):
        return ToolResult.fail(f"Нет шага с номером {index}.")
    _plan.steps[i].done = True
    _notify()
    return ToolResult.ok(_render())


def get_plan() -> ToolResult:
    """Возвращает текущий план и прогресс."""
    return ToolResult.ok(_render())


def reset_plan() -> None:
    _plan.steps = []
    _notify()


PLAN_DECLARATIONS = [
    {
        "name": "create_plan",
        "description": "Составить план из шагов для сложной многошаговой задачи. Вызывай В САМОМ НАЧАЛЕ, если задача требует нескольких действий.",
        "parameters": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Список шагов плана по порядку",
                }
            },
            "required": ["steps"],
        },
    },
    {
        "name": "complete_step",
        "description": "Отметить шаг плана выполненным (номер с 1) после его реального выполнения.",
        "parameters": {
            "type": "object",
            "properties": {"index": {"type": "integer", "description": "Номер шага с 1"}},
            "required": ["index"],
        },
    },
    {
        "name": "get_plan",
        "description": "Показать текущий план и прогресс.",
        "parameters": {"type": "object", "properties": {}},
    },
]

PLAN_HANDLERS = {
    "create_plan": create_plan,
    "complete_step": complete_step,
    "get_plan": get_plan,
}
