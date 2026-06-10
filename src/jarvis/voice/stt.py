"""Распознавание речи (STT) через Vosk — офлайн, бесплатно.

Требует:
  pip install vosk sounddevice
  и скачанную модель (напр. vosk-model-small-ru) в settings.vosk_model_path.
Модель: https://alphacephei.com/vosk/models (small-ru ~45 МБ).

Если зависимости/модель отсутствуют — возвращает понятную подсказку.
"""
from __future__ import annotations

import json
from pathlib import Path

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger

_SAMPLE_RATE = 16000


class STTResult:
    def __init__(self, ok: bool, text: str = "", error: str = "") -> None:
        self.ok = ok
        self.text = text
        self.error = error


def _check_deps() -> str | None:
    try:
        import sounddevice  # noqa: F401
        import vosk  # noqa: F401
    except ImportError:
        return "Распознавание недоступно: pip install vosk sounddevice"
    if not Path(settings.vosk_model_path).exists():
        return (
            f"Не найдена модель Vosk в {settings.vosk_model_path}. "
            "Скачайте vosk-model-small-ru с https://alphacephei.com/vosk/models "
            "и распакуйте туда."
        )
    return None


def transcribe_from_mic(seconds: float = 5.0) -> STTResult:
    """Записывает аудио с микрофона N секунд и распознаёт речь."""
    err = _check_deps()
    if err:
        return STTResult(False, error=err)

    try:
        import queue

        import sounddevice as sd
        import vosk

        model = vosk.Model(settings.vosk_model_path)
        rec = vosk.KaldiRecognizer(model, _SAMPLE_RATE)

        q: "queue.Queue[bytes]" = queue.Queue()

        def callback(indata, frames, time, status):  # noqa: ANN001, ARG001
            q.put(bytes(indata))

        import time as _time

        with sd.RawInputStream(
            samplerate=_SAMPLE_RATE, blocksize=8000, dtype="int16",
            channels=1, callback=callback,
        ):
            logger.info(f"STT: запись {seconds}с...")
            start = _time.time()
            while _time.time() - start < seconds:
                data = q.get()
                rec.AcceptWaveform(data)

        result = json.loads(rec.FinalResult())
        text = result.get("text", "").strip()
        return STTResult(True, text=text)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"STT ошибка: {e}")
        return STTResult(False, error=str(e))
