"""Долговременная память агента (между сессиями).

Хранит «факты» о пользователе и важные сведения из диалога. Под капотом —
тот же RAGStore (TF-IDF или эмбеддинги), но с отдельным файлом. Агент сам
решает, что запомнить (remember) и что вспомнить (recall); плюс релевантные
воспоминания автоматически подмешиваются в контекст.
"""
from __future__ import annotations

from jarvis.core.config import settings
from jarvis.rag.store import RAGStore


class LongTermMemory:
    """Тонкая обёртка над RAGStore для персональных фактов."""

    def __init__(self) -> None:
        # маленький размер чанка — память это короткие факты
        self._store = RAGStore(persist_path=settings.memory_db_path, chunk_size=400)
        self._counter = len(self._store.chunks)

    def remember(self, fact: str) -> int:
        """Сохраняет факт. Возвращает общее число воспоминаний."""
        self._counter += 1
        self._store.add_text(fact.strip(), source=f"mem#{self._counter}")
        return self.count()

    def recall(self, query: str, k: int | None = None):
        k = k or settings.memory_top_k
        return self._store.search(query, k=k)

    def count(self) -> int:
        return len({c.source for c in self._store.chunks})

    def clear(self) -> None:
        self._store.clear()
        self._counter = 0


# Singleton
long_term = LongTermMemory()
