# 📦 Сборка Jarvis в exe

Превращаем Jarvis в standalone exe-файлы через PyInstaller. После сборки агент работает на любой Windows-машине, где **не установлен Python**.

## ⚡ Быстрая сборка

В активированном venv (с префиксом `(.venv)` в строке):

```powershell
.\build_exe.bat
```

Скрипт сам поставит PyInstaller и соберёт два exe. Сборка занимает 1–3 минуты.

## 📁 Что получится

```
dist\
├── jarvis-console\
│   ├── jarvis-console.exe       ← консольный REPL
│   ├── _internal\               ← все DLL, библиотеки Python
│   └── .env.example
└── jarvis-server\
    ├── jarvis-server.exe        ← FastAPI сервер на :8000
    ├── _internal\
    └── .env.example
```

Размер каждой папки — около **150-250 МБ** (Python-рантайм + все зависимости + pyautogui + reportlab).

## 🚀 Как запускать

### Консольный режим

1. Скопируй папку `dist\jarvis-console\` куда угодно (например, на флэшку или в `Program Files`).
2. **Положи `.env` рядом с `jarvis-console.exe`** (не в `_internal\`!) — без него агент не получит ключ Gemini.
3. Двойной клик по `jarvis-console.exe` → откроется чёрное окно консоли:
   ```
   Jarvis консоль. Введите команду, 'exit' для выхода.
   Вы:
   ```

### Серверный режим (для мобильного приложения)

1. Папка `dist\jarvis-server\`, рядом — твой `.env`.
2. Двойной клик по `jarvis-server.exe` → запустится FastAPI на `0.0.0.0:8000`.
3. С телефона по Tailscale-IP — обычное подключение.

### Запуск из командной строки

```powershell
cd dist\jarvis-server
.\jarvis-server.exe
```

## ⚠️ Важные нюансы

### 1. .env должен быть рядом с exe

PyInstaller-приложения читают `.env` из текущей рабочей директории. Если запускаешь exe двойным кликом — рабочая директория = папка с exe. Если запускаешь из другого места, `.env` ищется там.

**Правило:** всегда копируй `.env` в ту же папку, где лежит `jarvis-console.exe` или `jarvis-server.exe`.

### 2. БД и логи создаются рядом

По умолчанию `DB_PATH=./data/jarvis.db`. Это путь относительно рабочей директории. После первого запуска появится папка `data\` с базой и логами.

### 3. Антивирус может ругаться

Свежесобранные PyInstaller-exe часто триггерят эвристики Windows Defender и других антивирусов. Это **ложное срабатывание** — bootloader PyInstaller выглядит для них подозрительно.

Решения:
- Добавить папку `dist\` в исключения антивируса
- Подписать exe сертификатом (платно, для серьёзного распространения)
- Использовать UPX-сжатие (но я выключил — оно делает ситуацию **хуже**, а не лучше)

### 4. Первый запуск медленный

PyInstaller-exe распаковывает себя в `%TEMP%` при каждом запуске — это занимает 1-3 секунды. Это нормально.

### 5. Windows Firewall спросит про сеть

При первом запуске `jarvis-server.exe` Windows покажет диалог "Защитник Windows Firewall заблокировал...". Нажми **"Разрешить доступ"** для частных сетей.

## 🐛 Если сборка падает

### `ModuleNotFoundError` после сборки

PyInstaller не нашёл какой-то динамически импортируемый модуль. Открой `jarvis.spec`, найди список `HIDDEN_IMPORTS` и добавь имя пакета.

Пример:
```python
HIDDEN_IMPORTS = [
    ...,
    "имя_недостающего_модуля",
]
```

Потом снова `.\build_exe.bat`.

### `Failed to execute script ...` без подробностей

Запусти exe из консоли (не двойным кликом) — увидишь полный traceback:
```powershell
cd dist\jarvis-console
.\jarvis-console.exe
```

### Хочется один exe-файл, а не папку

В `jarvis.spec` замени:
```python
exclude_binaries=True,   # ← было
```
на:
```python
exclude_binaries=False,
```

И убери блок `COLLECT(...)`. Это сделает **onefile**-сборку — один большой exe вместо папки. Запускается медленнее (10+ секунд на распаковку), но удобнее распространять.

### Нужен server без чёрного окна консоли (фоновая служба)

В `jarvis.spec`, в вызове `build_exe` для сервера поменяй:
```python
console=True,    # ← было
```
на:
```python
console=False,
```

Тогда exe запустится без видимого окна. Логи всё равно пишутся в `data\jarvis.log`.

## 🎁 Распространение (если нужно)

Самый простой способ упаковать всё для портфолио:

```powershell
cd dist
Compress-Archive -Path jarvis-server -DestinationPath jarvis-server.zip
Compress-Archive -Path jarvis-console -DestinationPath jarvis-console.zip
```

Положи zip в Releases на GitHub — пользователи скачают и запустят без установки Python.

Для красивого инсталлятора с ярлыками — посмотри **Inno Setup** (бесплатный): https://jrsoftware.org/isinfo.php
