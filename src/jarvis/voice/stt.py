"""Распознавание речи (STT) через Vosk — офлайн, бесплатно.

Пакеты: pip install vosk sounddevice
Модель скачивается автоматически при первом использовании (~45 МБ,
vosk-model-small-ru) в settings.vosk_model_path.
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger

_SAMPLE_RATE = 16000
_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"


class STTResult:
    def __init__(self, ok: bool, text: str = "", error: str = "") -> None:
        self.ok = ok
        self.text = text
        self.error = error


def deps_available() -> bool:
    try:
        import sounddevice  # noqa: F401
        import vosk  # noqa: F401

        return True
    except ImportError:
        return False


def model_present() -> bool:
    p = Path(settings.vosk_model_path)
    return p.exists() and any(p.iterdir()) if p.exists() else False


def ensure_model() -> bool:
    """Скачивает и распаковывает модель Vosk, если её ещё нет."""
    if model_present():
        return True
    dst = Path(settings.vosk_model_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp_zip = dst.parent / "_vosk_model.zip"
    try:
        import httpx

        logger.info(f"Скачиваю модель распознавания (~45 МБ): {_MODEL_URL}")
        with httpx.stream("GET", _MODEL_URL, timeout=120.0, follow_redirects=True) as r:
            r.raise_for_status()
            with open(tmp_zip, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=1 << 16):
                    f.write(chunk)
        with zipfile.ZipFile(tmp_zip) as z:
            extract_root = dst.parent / "_vosk_extract"
            if extract_root.exists():
                shutil.rmtree(extract_root)
            z.extractall(extract_root)
        # внутри zip — одна папка vosk-model-small-ru-0.22 → переносим в dst
        inner = next((p for p in extract_root.iterdir() if p.is_dir()), None)
        if inner is None:
            return False
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(inner), str(dst))
        logger.info(f"Модель распознавания установлена: {dst}")
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Не удалось скачать модель Vosk: {e}")
        return False
    finally:
        tmp_zip.unlink(missing_ok=True)
        shutil.rmtree(dst.parent / "_vosk_extract", ignore_errors=True)


def transcribe_from_mic(seconds: float = 5.0) -> STTResult:
    """Записывает аудио с микрофона N секунд и распознаёт речь."""
    if not deps_available():
        return STTResult(False, error="Распознавание недоступно: pip install vosk sounddevice")
    if not ensure_model():
        return STTResult(
            False,
            error="Не удалось получить модель распознавания. Проверьте интернет "
            "или скачайте вручную с alphacephei.com/vosk/models",
        )

    try:
        import queue
        import time as _time

        import sounddevice as sd
        import vosk

        model = vosk.Model(settings.vosk_model_path)
        rec = vosk.KaldiRecognizer(model, _SAMPLE_RATE)
        q: "queue.Queue[bytes]" = queue.Queue()

        def callback(indata, frames, time, status):  # noqa: ANN001, ARG001
            q.put(bytes(indata))

        with sd.RawInputStream(
            samplerate=_SAMPLE_RATE, blocksize=8000, dtype="int16",
            channels=1, callback=callback,
        ):
            logger.info(f"STT: запись {seconds}с...")
            start = _time.time()
            while _time.time() - start < seconds:
                data = q.get()
                rec.AcceptWaveform(data)

        text = json.loads(rec.FinalResult()).get("text", "").strip()
        return STTResult(True, text=text)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"STT ошибка: {e}")
        return STTResult(False, error=str(e))
