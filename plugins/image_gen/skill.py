"""Скилл генерации изображений через CogView-3-Flash (бесплатно, BigModel)."""
from __future__ import annotations

import time
from pathlib import Path

import httpx

from jarvis.core.config import settings
from jarvis.core.types import ToolResult

_MODEL = "cogview-3-flash"


def generate_image(prompt: str) -> ToolResult:
    """Генерирует изображение по текстовому описанию и сохраняет на диск."""
    if not settings.glm_api_key:
        return ToolResult.fail("Для генерации картинок нужен GLM_API_KEY (CogView).")
    url = f"{settings.glm_base_url.rstrip('/')}/images/generations"
    headers = {"Authorization": f"Bearer {settings.glm_api_key}"}
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json={"model": _MODEL, "prompt": prompt})
            if resp.status_code != 200:
                return ToolResult.fail(f"CogView {resp.status_code}: {resp.text[:200]}")
            img_url = (resp.json().get("data") or [{}])[0].get("url")
            if not img_url:
                return ToolResult.fail("CogView не вернул ссылку на изображение.")
            # скачиваем в безопасную зону
            img = client.get(img_url, timeout=120.0)
        out_dir = Path(settings.safe_root) / "jarvis_images"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"img_{int(time.time())}.png"
        out_path.write_bytes(img.content)
    except httpx.HTTPError as e:
        return ToolResult.fail(f"Ошибка генерации/скачивания: {e}")
    return ToolResult.ok(
        f"Изображение сгенерировано и сохранено: {out_path}",
        {"path": str(out_path), "url": img_url},
    )


DECLARATIONS = [
    {
        "name": "generate_image",
        "description": "Сгенерировать изображение по текстовому описанию (CogView). Используй, когда просят нарисовать/создать картинку.",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Описание желаемого изображения"}
            },
            "required": ["prompt"],
        },
    }
]

HANDLERS = {"generate_image": generate_image}
