"""Унифицированный формат результата работы инструментов.

ТЗ требует: каждая функция возвращает {status, message, data?}.
Используем pydantic — гарантия структуры на этапе типизации.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ToolResult(BaseModel):
    """Унифицированный ответ исполнителя."""

    status: Literal["success", "error"]
    message: str
    data: dict[str, Any] | None = None

    @classmethod
    def ok(cls, message: str, data: dict[str, Any] | None = None) -> "ToolResult":
        return cls(status="success", message=message, data=data)

    @classmethod
    def fail(cls, message: str, data: dict[str, Any] | None = None) -> "ToolResult":
        return cls(status="error", message=message, data=data)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
