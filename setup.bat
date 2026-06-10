@echo off
REM Быстрая установка зависимостей и запуск Jarvis на Windows.
REM Запуск: setup.bat

echo === Jarvis setup ===

if not exist .venv (
    echo [1/4] Creating virtualenv...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .

if not exist .env (
    echo [3/4] Creating .env from template...
    copy .env.example .env
    echo.
    echo !!! Edit .env and set GEMINI_API_KEY before running.
    echo Get a free key at https://aistudio.google.com/app/apikey
)

echo [4/4] Done. Run:
echo   .venv\Scripts\activate
echo   python -m jarvis.console      ^(local REPL^)
echo   python -m jarvis.main         ^(server on :8000^)
