@echo off
REM Сборка exe-версий Jarvis через PyInstaller.
REM Требования: активированное venv с установленным pyinstaller.

echo === Building Jarvis exe ===

REM Активируем venv, если ещё не активирован
if not defined VIRTUAL_ENV (
    if exist .venv\Scripts\activate.bat (
        call .venv\Scripts\activate.bat
    ) else (
        echo [ERROR] venv not found. Run setup.bat first.
        exit /b 1
    )
)

REM Убедимся, что pyinstaller установлен
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
)

REM Чистим старую сборку
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist

REM Сборка
python -m PyInstaller jarvis.spec --clean --noconfirm

if errorlevel 1 (
    echo [ERROR] Build failed.
    exit /b 1
)

echo.
echo === Build complete ===
echo.
echo Console version:  dist\jarvis-console\jarvis-console.exe
echo Server version:   dist\jarvis-server\jarvis-server.exe
echo.
echo IMPORTANT: copy your .env file next to the .exe before running.
echo.
