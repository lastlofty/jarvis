"""Лёгкий RAG-стор без внешних зависимостей.

Документы режутся на чанки и индексируются по TF-IDF (мешок слов с весами).
Поиск — косинусная близость разреженных векторов. Этого достаточно для базы
знаний портфолио и личного использования; при желании позже можно подменить
на эмбеддинги, не меняя интерфейс.
"""
from __future__ import annotations

import math
import pickle
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger

_WORD_RE = re.compile(r"[а-яёa-z0-9_]+", re.IGNORECASE)
_INDEXABLE_SUFFIXES = {".txt", ".md", ".py", ".json", ".csv", ".rst", ".log"}


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


@dataclass
class Chunk:
    """Фрагмент документа с частотами слов и (опц.) эмбеддингом."""

    source: str
    text: str
    tf: Counter[str] = field(default_factory=Counter)
    vec: list[float] | None = None

    def __post_init__(self) -> None:
        if not self.tf:
            self.tf = Counter(_tokenize(self.text))


@dataclass
class SearchHit:
    source: str
    text: str
    score: float


class RAGStore:
    """Хранилище чанков с TF-IDF поиском и персистентностью в pickle."""

    def __init__(self, persist_path: str | None = None, chunk_size: int = 800) -> None:
        self.persist_path = Path(persist_path or settings.rag_db_path)
        self.chunk_size = chunk_size
        self.chunks: list[Chunk] = []
        self._idf: dict[str, float] = {}
        self._load()

    # ---------- персистентность ----------
    def _load(self) -> None:
        try:
            with open(self.persist_path, "rb") as f:
                self.chunks = pickle.load(f)
            self._recompute_idf()
            logger.info(f"RAG загружен: {len(self.chunks)} чанков")
        except (FileNotFoundError, EOFError, pickle.UnpicklingError):
            self.chunks = []

    def _save(self) -> None:
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, "wb") as f:
            pickle.dump(self.chunks, f)

    # ---------- индексация ----------
    @staticmethod
    def _split(text: str, size: int) -> Iterable[str]:
        """Режет текст на чанки по абзацам, не разрывая слова грубо."""
        paragraphs = re.split(r"\n\s*\n", text)
        buf = ""
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if len(buf) + len(p) + 2 <= size:
                buf = f"{buf}\n\n{p}" if buf else p
            else:
                if buf:
                    yield buf
                # длинный абзац — режем жёстко
                while len(p) > size:
                    yield p[:size]
                    p = p[size:]
                buf = p
        if buf:
            yield buf

    def add_text(self, text: str, source: str) -> int:
        """Индексирует строку под именем source. Возвращает число чанков."""
        # выбрасываем старые чанки этого источника (переиндексация)
        self.chunks = [c for c in self.chunks if c.source != source]
        new_chunks: list[Chunk] = []
        for piece in self._split(text, self.chunk_size):
            new_chunks.append(Chunk(source=source, text=piece))

        # опциональные эмбеддинги (с откатом на TF-IDF при недоступности)
        from jarvis.rag import embeddings

        if embeddings.available() and new_chunks:
            vecs = embeddings.embed([c.text for c in new_chunks])
            if vecs and len(vecs) == len(new_chunks):
                for c, v in zip(new_chunks, vecs):
                    c.vec = v

        self.chunks.extend(new_chunks)
        self._recompute_idf()
        self._save()
        return len(new_chunks)

    def add_file(self, path: str | Path) -> int:
        p = Path(path)
        if p.suffix.lower() not in _INDEXABLE_SUFFIXES:
            return 0
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            logger.warning(f"RAG не смог прочитать {p}: {e}")
            return 0
        return self.add_text(text, source=str(p))

    def index_folder(self, folder: str | Path) -> dict[str, int]:
        """Рекурсивно индексирует подходящие файлы папки."""
        folder = Path(folder)
        results: dict[str, int] = {}
        if not folder.exists():
            logger.warning(f"RAG: папки нет — {folder}")
            return results
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in _INDEXABLE_SUFFIXES:
                n = self.add_file(path)
                if n:
                    results[str(path)] = n
        logger.info(f"RAG проиндексировал {len(results)} файлов из {folder}")
        return results

    # ---------- поиск ----------
    def _recompute_idf(self) -> None:
        n_docs = len(self.chunks)
        df: Counter[str] = Counter()
        for c in self.chunks:
            df.update(c.tf.keys())
        self._idf = {
            term: math.log((1 + n_docs) / (1 + freq)) + 1.0 for term, freq in df.items()
        }

    def _vector(self, tf: Counter[str]) -> dict[str, float]:
        return {t: f * self._idf.get(t, 1.0) for t, f in tf.items()}

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        dot = sum(a[t] * b[t] for t in common)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    @staticmethod
    def _cosine_vec(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    def search(self, query: str, k: int = 3) -> list[SearchHit]:
        if not self.chunks:
            return []

        # семантический поиск, если есть эмбеддинги
        from jarvis.rag import embeddings

        if embeddings.available() and any(c.vec for c in self.chunks):
            qvec = embeddings.embed_one(query)
            if qvec:
                scored = [
                    SearchHit(c.source, c.text, self._cosine_vec(qvec, c.vec))
                    for c in self.chunks
                    if c.vec
                ]
                scored.sort(key=lambda h: h.score, reverse=True)
                return scored[:k]

        # откат на TF-IDF
        qv = self._vector(Counter(_tokenize(query)))
        scored = [
            SearchHit(c.source, c.text, self._cosine(qv, self._vector(c.tf)))
            for c in self.chunks
        ]
        scored = [h for h in scored if h.score > 0]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]

    def clear(self) -> None:
        self.chunks = []
        self._idf = {}
        self._save()

    def stats(self) -> dict[str, int]:
        sources = {c.source for c in self.chunks}
        return {"chunks": len(self.chunks), "sources": len(sources)}


# Singleton
rag = RAGStore()
