# 🗺 Roadmap

## ✅ Фаза 1 — Ядро (готово)
- [x] Observer: активное окно, фоновое отслеживание времени
- [x] SQLite: app_usage, action_log, dialog_history
- [x] LLM-оркестратор на Gemini с function calling
- [x] Инструменты: файлы, ввод, запуск приложений, отчёты
- [x] safety guard (SAFE_ROOT)
- [x] Краткосрочная память (deque на 20)

## ✅ Фаза 2 — Сетевая (готово)
- [x] FastAPI: `/command`, `/screenshot`, `/health`
- [x] WebSocket `/ws` с Bearer-аутентификацией
- [x] CommunicationBridge для `ask_user` через WebSocket
- [x] CI: ruff + black + mypy + pytest

## 🔜 Фаза 3 — Flutter-приложение

**Цель:** один экран чата + экран скриншота + настройки.

Минимальный план:
- `lib/api/jarvis_client.dart` — WebSocket-клиент с авто-reconnect
- `lib/screens/chat_screen.dart` — список сообщений + поле ввода
- `lib/screens/screen_viewer.dart` — `Image.network` с pull-to-refresh
- `lib/screens/settings_screen.dart` — host/port/token

Зависимости: `web_socket_channel`, `provider`, `shared_preferences`, `http`.

> Я (Claude) могу сгенерировать код Flutter-приложения отдельным сообщением — попроси: «дай Flutter-часть».

## 🔜 Фаза 4 — Долговременная память

Идея: каждый успешно выполненный пользовательский интент → эмбеддинг (sentence-transformers/all-MiniLM-L6-v2) → таблица `memory_store`. При новом запросе: top-3 ближайших по cosine добавляются в системный промпт как примеры.

Файлы:
- `src/jarvis/memory/long_term.py` — индекс и поиск
- Расширить `db.py` таблицей `memory_store(id, ts, intent, action, outcome, embedding BLOB)`
- Орекстратор подмешивает ближайшие примеры перед каждым ответом LLM

## 🔜 Фаза 5 — WebRTC живой экран

`aiortc` (Python) → `flutter_webrtc`. Сигнализация через тот же WebSocket. Захват экрана — `mss`, кодирование в VP8 30fps.

## 🔜 Фаза 6 — Плагины

Entry-points в `pyproject.toml`:
```toml
[project.entry-points."jarvis.tools"]
spotify = "jarvis_plugin_spotify:tools"
```
Загрузчик в `executor/registry.py` будет автоматически подцеплять новые инструменты.
