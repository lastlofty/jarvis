"""Защита сервера: проверка токена и анти-брутфорс.

- Сравнение токена в постоянном времени (защита от timing-атак).
- Слабый/дефолтный токен => сервер НЕ пускает никого (secure-by-default).
- Блокировка IP после серии неудачных попыток (анти-брутфорс).
"""
from __future__ import annotations

import secrets
import threading
import time

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger

# Токены, которые считаются «не заданными»
_DEFAULT_TOKENS = {"", "change_me_to_random_secret", "change_me"}
MIN_TOKEN_LEN = 16

# Параметры анти-брутфорса
_MAX_FAILS = 5
_LOCKOUT_SEC = 300

_lock = threading.Lock()
_fails: dict[str, list[float]] = {}  # ip -> [count, lock_until_ts]


def token_is_weak() -> bool:
    t = (settings.auth_token or "").strip()
    return t in _DEFAULT_TOKENS or len(t) < MIN_TOKEN_LEN


def check_token(provided: str | None) -> bool:
    """True только если токен задан надёжно и совпадает (constant-time)."""
    if token_is_weak() or not provided:
        return False
    return secrets.compare_digest(provided.strip(), settings.auth_token.strip())


def lock_remaining(ip: str) -> float:
    """Сколько секунд осталось до конца блокировки IP (0 — не заблокирован)."""
    with _lock:
        rec = _fails.get(ip)
        if not rec:
            return 0.0
        rem = rec[1] - time.time()
        return rem if rem > 0 else 0.0


def record_fail(ip: str) -> None:
    with _lock:
        rec = _fails.setdefault(ip, [0.0, 0.0])
        rec[0] += 1
        if rec[0] >= _MAX_FAILS:
            rec[1] = time.time() + _LOCKOUT_SEC
            logger.warning(
                f"Анти-брутфорс: IP {ip} заблокирован на {_LOCKOUT_SEC}s "
                f"после {int(rec[0])} неудачных попыток авторизации"
            )


def record_success(ip: str) -> None:
    with _lock:
        _fails.pop(ip, None)


def warn_if_weak() -> None:
    if token_is_weak():
        logger.warning(
            "БЕЗОПАСНОСТЬ: AUTH_TOKEN не задан или слишком короткий — сервер "
            "БЛОКИРУЕТ все запросы. Задайте надёжный AUTH_TOKEN (>=16 символов) "
            "в .env. Сгенерировать: python -c \"import secrets;print(secrets.token_urlsafe(32))\""
        )
