"""Краткосрочная память: кольцевой буфер последних N сообщений диалога."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator, Literal


Role = Literal["user", "assistant", "system", "tool"]


@dataclass
class Message:
    role: Role
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }


class ShortTermMemory:
    """Хранит последние `max_size` сообщений диалога."""

    def __init__(self, max_size: int = 20) -> None:
        self._buffer: deque[Message] = deque(maxlen=max_size)

    def add(self, role: Role, content: str) -> None:
        self._buffer.append(Message(role=role, content=content))

    def __iter__(self) -> Iterator[Message]:
        return iter(self._buffer)

    def __len__(self) -> int:
        return len(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()

    def as_list(self) -> list[Message]:
        return list(self._buffer)
