"""Озвучка ответов (TTS).

По умолчанию — офлайн через pyttsx3 (Windows SAPI5, работает без интернета и
без скачивания моделей). Речь произносится в фоновом потоке, чтобы не блокировать
GUI. Если pyttsx3 не установлен — методы тихо ничего не делают.
"""
from __future__ import annotations

import threading

from jarvis.core.logging_setup import logger


class TTS:
    """Простой потокобезопасный движок озвучки."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is None:
            try:
                import pyttsx3  # noqa: F401

                self._available = True
            except Exception:  # noqa: BLE001
                self._available = False
                logger.info("TTS недоступен: pip install pyttsx3")
        return self._available

    def _speak_blocking(self, text: str) -> None:
        try:
            import pyttsx3

            engine = pyttsx3.init()
            # пробуем русский голос, если есть (languages может быть str или bytes)
            for v in engine.getProperty("voices"):
                name = (getattr(v, "name", "") or "").lower()
                langs = getattr(v, "languages", []) or []
                langs_str = " ".join(
                    (x.decode("utf-8", "ignore") if isinstance(x, bytes) else str(x))
                    for x in langs
                ).lower()
                if "rus" in name or "irina" in name or "ru" in langs_str:
                    engine.setProperty("voice", v.id)
                    break
            engine.setProperty("rate", 180)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"TTS ошибка: {e}")

    def speak(self, text: str) -> None:
        """Произносит текст в фоновом потоке (не блокирует вызывающий код)."""
        if not text or not self.is_available():
            return

        def run() -> None:
            with self._lock:
                self._speak_blocking(text)

        threading.Thread(target=run, daemon=True, name="TTS").start()


# Singleton
tts = TTS()
