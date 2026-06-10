# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для Jarvis.

Собирает ДВА exe одной командой:
  - jarvis-console.exe — консольный REPL
  - jarvis-server.exe  — FastAPI сервер на :8000

Использование:
    pyinstaller jarvis.spec --clean --noconfirm

Результат: dist/jarvis-console/, dist/jarvis-server/

Каждая папка содержит .exe + DLL'и + папку _internal/. Папку целиком копируешь
куда угодно, .env кладёшь рядом с exe.
"""

import sys
from pathlib import Path

# Скрытые импорты — PyInstaller сам не находит динамически загружаемые модули
HIDDEN_IMPORTS = [
    # Pydantic (рантайм-валидация)
    "pydantic",
    "pydantic_settings",
    "pydantic.deprecated.decorator",

    # Google Gen AI SDK тащит за собой много, не всё ловится автоматически
    "google.generativeai",
    "google.ai.generativelanguage",
    "google.api_core",
    "google.auth",
    "grpc",
    "grpc._cython.cygrpc",

    # Uvicorn loops/protocols
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",

    # FastAPI/Starlette
    "fastapi",
    "starlette.routing",
    "websockets.legacy",
    "websockets.legacy.server",

    # Reportlab (для PDF-отчётов)
    "reportlab.pdfbase._fontdata_enc_winansi",
    "reportlab.pdfbase._fontdata_enc_macroman",
    "reportlab.pdfbase._fontdata_enc_standard",
    "reportlab.pdfbase._fontdata_enc_symbol",
    "reportlab.pdfbase._fontdata_enc_zapfdingbats",
    "reportlab.pdfbase._fontdata_widths_helvetica",

    # mss (скриншоты на Windows)
    "mss.windows",

    # pywin32 (имя процесса активного окна)
    "win32gui",
    "win32process",
    "win32api",
    "win32con",

    # pyautogui тащит подмодули
    "pyautogui",
    "pyscreeze",
    "pymsgbox",
    "pytweening",
    "mouseinfo",
]

# Файлы данных, которые нужно положить РЯДОМ с exe
DATAS = [
    # .env.example — чтобы пользователь знал, какие переменные настраивать
    (".env.example", "."),
    # Мобильное PWA-приложение (раздаётся сервером на /app)
    ("src/jarvis/server/webapp", "jarvis/server/webapp"),
]


def build_exe(name: str, script: str, console: bool):
    """Возвращает (Analysis, PYZ, EXE, COLLECT) для одного исполняемого."""
    a = Analysis(
        [script],
        pathex=["src"],
        binaries=[],
        datas=DATAS,
        hiddenimports=HIDDEN_IMPORTS,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[
            # Не нужны в проде — экономим вес
            "tkinter",
            "matplotlib",
            "test",
            "tests",
            "unittest",
            "pytest",
        ],
        noarchive=False,
        optimize=0,
    )
    pyz = PYZ(a.pure)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,        # UPX делает антивирусы ещё подозрительнее
        console=console,  # True для консольного REPL, False для сервера
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=name,
    )
    return coll


# Консольный REPL (с консолью — пользователь печатает в окно)
console_collect = build_exe(
    name="jarvis-console",
    script="src/jarvis/console.py",
    console=True,
)

# Сервер (тоже с консолью — чтобы видеть логи; иначе console=False для фоновой)
server_collect = build_exe(
    name="jarvis-server",
    script="src/jarvis/main.py",
    console=True,
)
