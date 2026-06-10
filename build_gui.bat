@echo off
REM Сборка GUI-версии Jarvis в exe.

echo === Building Jarvis GUI ===

if not defined VIRTUAL_ENV (
    if exist .venv\Scripts\activate.bat (
        call .venv\Scripts\activate.bat
    ) else (
        echo [ERROR] venv not found. Run setup.bat first.
        exit /b 1
    )
)

REM PyInstaller
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
)

REM PySide6
python -m pip show PySide6 >nul 2>&1
if errorlevel 1 (
    echo Installing PySide6...
    python -m pip install PySide6
)

REM Чистим прошлую сборку
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist

python -m PyInstaller jarvis_gui.spec --clean --noconfirm

if errorlevel 1 (
    echo [ERROR] Build failed.
    exit /b 1
)

REM Копируем рядом с exe пользовательские файлы (редактируемые, не в бандле)
echo Copying runtime files next to exe...
xcopy /E /I /Y plugins "dist\Jarvis\plugins" >nul
if exist mcp_servers.json copy /Y mcp_servers.json "dist\Jarvis\" >nul
if exist .env.example copy /Y .env.example "dist\Jarvis\" >nul
REM Переносим .env, если есть (иначе пользователь создаст из .env.example)
if exist .env copy /Y .env "dist\Jarvis\" >nul

echo.
echo === Build complete ===
echo.
echo Result: dist\Jarvis\Jarvis.exe
echo.
echo Папка dist\Jarvis готова к переносу куда угодно.
echo   - plugins\, .env, mcp_servers.json лежат рядом с exe (редактируемые)
echo   - если нет .env — скопируйте .env.example в .env и впишите ключ GLM
echo   - запуск: двойной клик по Jarvis.exe
echo.
