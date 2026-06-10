# 🧪 Тестирование без мобильного приложения

## 1. Консольный REPL

Самый простой способ убедиться, что всё работает:

```bash
python -m jarvis.console
```

**Сценарии для проверки:**

| # | Команда | Что должно произойти |
|---|---|---|
| 1 | `создай папку проекты` | На рабочем столе появится `проекты/` |
| 2 | `создай в ней файл readme.txt с текстом "привет мир"` | Появится `проекты/readme.txt` |
| 3 | `покажи список файлов в папке проекты` | Список с `readme.txt` |
| 4 | `сколько времени я провёл в браузере за последние сутки?` | Цифра из `app_usage` |
| 5 | `сделай скриншот` | Путь к PNG в temp-папке |
| 6 | `удали файл readme.txt в папке проекты` | Сначала вопрос на подтверждение, потом удаление |
| 7 | `открой блокнот` | Запустится notepad.exe |
| 8 | `создай отчёт за сегодня в формате pdf` | PDF в temp |

## 2. REST через curl

```bash
# Запустить сервер
python -m jarvis.main

# В другом терминале:
TOKEN=<значение из .env>

curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}

curl -X POST http://localhost:8000/command \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"создай папку test_via_api"}'

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/screenshot --output shot.png
```

## 3. WebSocket через wscat / websocat

Установка: `npm install -g wscat`

```bash
wscat -c ws://localhost:8000/ws

# 1. Аутентификация
> {"type":"auth","token":"<AUTH_TOKEN>"}
< {"type":"auth","ok":true}

# 2. Команда
> {"type":"command","text":"создай папку из_ws"}
< {"type":"status","status":"in_progress"}
< {"type":"status","status":"done","message":"Готово, создал папку..."}

# 3. Если агент задал вопрос:
< {"type":"question","id":1,"question":"Удалить файл? Это необратимо."}
> {"type":"answer","id":1,"answer":"да"}
```

## 4. Юнит-тесты

```bash
make test
# или
pytest --cov=src/jarvis --cov-report=html
# отчёт: htmlcov/index.html
```

## 5. Без Gemini-ключа

Чтобы протестировать всё, кроме LLM, импортируйте инструменты напрямую:

```python
import asyncio
from jarvis.executor.registry import dispatch

async def main():
    print(await dispatch("create_folder", {"path": ".", "folder_name": "demo"}))
    print(await dispatch("list_directory", {"path": "."}))

asyncio.run(main())
```
