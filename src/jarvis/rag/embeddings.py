"""Эмбеддинги через GLM (embedding-3) для семантического поиска.

Бесплатный векторный поиск поверх API GLM. Если ключа нет или произошла
ошибка — возвращает None, и вызывающий код откатывается на TF-IDF.
"""
from __future__ import annotations

import httpx

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger


def available() -> bool:
    return bool(settings.rag_embeddings and settings.glm_api_key)


def embed(texts: list[str]) -> list[list[float]] | None:
    """Возвращает список векторов для текстов (или None при недоступности)."""
    if not texts or not settings.glm_api_key:
        return None
    url = f"{settings.glm_base_url.rstrip('/')}/embeddings"
    headers = {"Authorization": f"Bearer {settings.glm_api_key}"}
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                url, headers=headers,
                json={"model": settings.embedding_model, "input": texts},
            )
        if resp.status_code != 200:
            logger.warning(f"Эмбеддинги {resp.status_code}: {resp.text[:200]}")
            return None
        data = resp.json().get("data", [])
        return [item["embedding"] for item in data]
    except httpx.HTTPError as e:
        logger.warning(f"Эмбеддинги: ошибка соединения {e}")
        return None


def embed_one(text: str) -> list[float] | None:
    vecs = embed([text])
    return vecs[0] if vecs else None
