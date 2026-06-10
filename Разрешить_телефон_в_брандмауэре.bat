@echo off
chcp 65001 >nul
title Jarvis - правило брандмауэра для телефона

REM Открывает порт 8000 для входящих подключений (телефон -> ПК).
REM ЗАПУСКАТЬ ОТ ИМЕНИ АДМИНИСТРАТОРА (правый клик -> Запуск от имени администратора).

net session >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Нужны права администратора.
    echo Правый клик по файлу -^> "Запуск от имени администратора".
    echo.
    pause
    exit /b 1
)

netsh advfirewall firewall delete rule name="Jarvis Mobile" >nul 2>&1
netsh advfirewall firewall add rule name="Jarvis Mobile" dir=in action=allow protocol=TCP localport=8000

echo.
echo Готово! Порт 8000 открыт для телефона.
echo Теперь в Jarvis: Настройки -^> "Запустить сервер для телефона" -^> сканируй QR.
echo.
pause
