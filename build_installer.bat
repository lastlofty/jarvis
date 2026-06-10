@echo off
chcp 65001 >nul
REM Сборка установщика Jarvis через Inno Setup.
REM Требует: 1) собранную папку dist\Jarvis (build_gui.bat)
REM          2) установленный Inno Setup 6 (ISCC.exe)

cd /d "%~dp0"

if not exist "dist\Jarvis\Jarvis.exe" (
    echo [ОШИБКА] Нет dist\Jarvis\Jarvis.exe — сначала запустите build_gui.bat
    pause
    exit /b 1
)

REM Ищем компилятор Inno Setup
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo [ОШИБКА] Inno Setup не найден.
    echo Установите его одной командой:
    echo     winget install JRSoftware.InnoSetup
    echo или скачайте: https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)

echo Компиляция установщика...
"%ISCC%" installer.iss
if errorlevel 1 (
    echo [ОШИБКА] Сборка установщика не удалась.
    pause
    exit /b 1
)

echo.
echo === Готово ===
echo Установщик: installer_out\Jarvis-Setup-0.2.0.exe
echo.
pause
