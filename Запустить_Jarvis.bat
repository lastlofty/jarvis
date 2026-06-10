@echo off
chcp 65001 >nul
title Jarvis AI Agent
cd /d "%~dp0"

echo.
echo   == Запуск Jarvis ==
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ОШИБКА] Не найдено виртуальное окружение .venv
    echo Создайте его:  python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt ^&^& .venv\Scripts\pip install -e .
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m jarvis.gui

if errorlevel 1 (
    echo.
    echo [Jarvis завершился с ошибкой] См. сообщения выше и data\jarvis.log
    pause
)
