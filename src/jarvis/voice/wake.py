"""Активация по ключевому слову («джарвис»).

Постоянно слушает микрофон через Vosk (офлайн) в фоновом потоке. При
распознавании слова активации отдаёт Qt-сигнал. Опционально и мягко
деградирует, если нет vosk/sounddevice/модели или выключено в настройках.
"""
from __future__ import annotations

import json
import threading

from PySide6.QtCore import QObject, Signal

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger

_SR = 16000


class WakeWord(QObject):
    detected = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> bool:
        if not settings.wake_word_enabled:
            return False
        try:
            import sounddevice  # noqa: F401
            import vosk  # noqa: F401
        except ImportError:
            logger.info("Wake-word недоступно: pip install vosk sounddevice")
            return False
        from pathlib import Path

        if not Path(settings.vosk_model_path).exists():
            logger.info("Wake-word: не найдена модель Vosk")
            return False

        self._thread = threading.Thread(target=self._run, daemon=True, name="WakeWord")
        self._thread.start()
        logger.info(f"Wake-word активно: слово «{settings.wake_word}»")
        return True

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        import queue

        import sounddevice as sd
        import vosk

        word = settings.wake_word.lower()
        model = vosk.Model(settings.vosk_model_path)
        rec = vosk.KaldiRecognizer(model, _SR)
        q: "queue.Queue[bytes]" = queue.Queue()

        def cb(indata, frames, time, status):  # noqa: ANN001, ARG001
            q.put(bytes(indata))

        try:
            with sd.RawInputStream(samplerate=_SR, blocksize=8000, dtype="int16",
                                   channels=1, callback=cb):
                while not self._stop.is_set():
                    data = q.get()
                    if rec.AcceptWaveform(data):
                        text = json.loads(rec.Result()).get("text", "")
                    else:
                        text = json.loads(rec.PartialResult()).get("partial", "")
                    if word in text.lower():
                        self.detected.emit()
                        rec = vosk.KaldiRecognizer(model, _SR)  # сброс, чтобы не триггерить повторно
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Wake-word остановлено: {e}")


wake_word = WakeWord()
