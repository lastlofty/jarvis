"""Скилл погоды через open-meteo (бесплатно, без ключа)."""
from __future__ import annotations

import httpx

from jarvis.core.types import ToolResult

# Коды погоды WMO -> текст
_WMO = {
    0: "ясно", 1: "в основном ясно", 2: "переменная облачность", 3: "пасмурно",
    45: "туман", 48: "изморозь", 51: "морось", 53: "морось", 55: "сильная морось",
    61: "небольшой дождь", 63: "дождь", 65: "сильный дождь",
    71: "небольшой снег", 73: "снег", 75: "сильный снег", 77: "снежные зёрна",
    80: "ливень", 81: "ливень", 82: "сильный ливень",
    95: "гроза", 96: "гроза с градом", 99: "гроза с градом",
}


def get_weather(city: str) -> ToolResult:
    """Возвращает текущую погоду в указанном городе."""
    try:
        with httpx.Client(timeout=20.0) as client:
            geo = client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "ru"},
            ).json()
            results = geo.get("results")
            if not results:
                return ToolResult.fail(f"Город не найден: {city}")
            loc = results[0]
            lat, lon = loc["latitude"], loc["longitude"]
            name = loc.get("name", city)
            country = loc.get("country", "")

            wx = client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
                },
            ).json()
    except httpx.HTTPError as e:
        return ToolResult.fail(f"Ошибка получения погоды: {e}")

    cur = wx.get("current", {})
    code = cur.get("weather_code")
    desc = _WMO.get(code, "—")
    temp = cur.get("temperature_2m")
    feels = cur.get("apparent_temperature")
    hum = cur.get("relative_humidity_2m")
    wind = cur.get("wind_speed_10m")

    text = (
        f"Погода в {name}{', ' + country if country else ''}: {desc}, "
        f"{temp}°C (ощущается {feels}°C), влажность {hum}%, ветер {wind} км/ч."
    )
    return ToolResult.ok(
        text,
        {"city": name, "temp": temp, "feels_like": feels, "humidity": hum,
         "wind": wind, "description": desc},
    )


DECLARATIONS = [
    {
        "name": "get_weather",
        "description": "Узнать текущую погоду в городе. Используй при вопросах о погоде.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "Название города"}},
            "required": ["city"],
        },
    }
]

HANDLERS = {"get_weather": get_weather}
