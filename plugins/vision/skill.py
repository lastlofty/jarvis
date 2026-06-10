"""Скилл «Зрение»: Jarvis видит экран и изображения через GLM-4V.

Использует бесплатную мультимодальную модель glm-4v-flash (Zhipu / BigModel).
Ключ берётся из настроек GLM (settings.glm_api_key).
"""
from __future__ import annotations

import base64
from pathlib import Path

import httpx

from jarvis.core.config import settings
from jarvis.core.types import ToolResult

_VISION_MODEL = "glm-4v-flash"


def _ask_vision(image_b64: str, question: str) -> ToolResult:
    if not settings.glm_api_key:
        return ToolResult.fail("Для зрения нужен GLM_API_KEY (модель glm-4v-flash).")
    url = f"{settings.glm_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": _VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": image_b64}},
                ],
            }
        ],
    }
    headers = {"Authorization": f"Bearer {settings.glm_api_key}"}
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as e:
        return ToolResult.fail(f"Ошибка обращения к GLM-4V: {e}")
    if resp.status_code != 200:
        return ToolResult.fail(f"GLM-4V {resp.status_code}: {resp.text[:200]}")
    msg = (resp.json().get("choices") or [{}])[0].get("message", {})
    answer = msg.get("content") or "(пустой ответ)"
    return ToolResult.ok(answer, {"model": _VISION_MODEL})


def analyze_screen(question: str = "Что изображено на экране? Опиши подробно.") -> ToolResult:
    """Делает скриншот экрана и анализирует его через GLM-4V."""
    from jarvis.executor.input_tools import take_screenshot

    shot = take_screenshot()
    if shot.status != "success" or not shot.data:
        return ToolResult.fail(f"Не удалось сделать скриншот: {shot.message}")
    path = Path(shot.data["path"])
    try:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError as e:
        return ToolResult.fail(f"Не удалось прочитать скриншот: {e}")
    return _ask_vision(b64, question)


def analyze_image(path: str, question: str = "Что на этом изображении?") -> ToolResult:
    """Анализирует изображение по пути через GLM-4V."""
    p = Path(path)
    if not p.exists():
        return ToolResult.fail(f"Файл не найден: {path}")
    try:
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    except OSError as e:
        return ToolResult.fail(f"Не удалось прочитать файл: {e}")
    return _ask_vision(b64, question)


DECLARATIONS = [
    {
        "name": "analyze_screen",
        "description": "Сделать скриншот экрана и проанализировать его (зрение GLM-4V). Используй, когда спрашивают «что на экране», «что я делаю», «помоги с тем что вижу».",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Что именно спросить про экран"}
            },
        },
    },
    {
        "name": "analyze_image",
        "description": "Проанализировать изображение по пути к файлу (зрение GLM-4V).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Путь к изображению"},
                "question": {"type": "string", "description": "Что спросить про изображение"},
            },
            "required": ["path"],
        },
    },
]

HANDLERS = {"analyze_screen": analyze_screen, "analyze_image": analyze_image}
