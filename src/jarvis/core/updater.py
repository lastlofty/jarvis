"""Проверка обновлений через GitHub Releases.

Сравнивает текущую версию (jarvis.__version__) с последним релизом на GitHub.
Тихо ничего не делает, если выключено, нет сети или репозиторий недоступен.
Само скачивание/замена exe не делается автоматически (на Windows нельзя
перезаписать запущенный exe) — пользователю показывается уведомление со ссылкой
на установщик новой версии.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from jarvis import __version__
from jarvis.core.config import settings
from jarvis.core.logging_setup import logger


@dataclass
class UpdateInfo:
    version: str
    url: str
    notes: str
    download_url: str | None = None


def _parse(v: str) -> tuple[int, ...]:
    v = v.strip().lstrip("vV")
    parts = []
    for p in v.split("."):
        num = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts) or (0,)


def is_newer(remote: str, local: str) -> bool:
    return _parse(remote) > _parse(local)


def check_for_update() -> UpdateInfo | None:
    """Возвращает информацию об обновлении или None."""
    if not settings.update_check or not settings.update_repo:
        return None
    api = f"https://api.github.com/repos/{settings.update_repo}/releases/latest"
    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            resp = client.get(api, headers={"Accept": "application/vnd.github+json"})
        if resp.status_code != 200:
            logger.info(f"Проверка обновлений: HTTP {resp.status_code}")
            return None
        data = resp.json()
    except httpx.HTTPError as e:
        logger.info(f"Проверка обновлений недоступна: {e}")
        return None

    tag = data.get("tag_name", "")
    if not tag or not is_newer(tag, __version__):
        return None

    # ищем .exe-ассет установщика, если есть
    download = None
    for asset in data.get("assets", []):
        name = asset.get("name", "").lower()
        if name.endswith(".exe"):
            download = asset.get("browser_download_url")
            break

    info = UpdateInfo(
        version=tag.lstrip("vV"),
        url=data.get("html_url", ""),
        notes=(data.get("body") or "")[:300],
        download_url=download,
    )
    logger.info(f"Доступно обновление: {info.version}")
    return info
