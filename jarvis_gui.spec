# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для GUI-версии Jarvis.

Использование:
    pyinstaller jarvis_gui.spec --clean --noconfirm

Результат: dist/Jarvis/Jarvis.exe (windowed, без чёрной консоли)
"""

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

HIDDEN_IMPORTS = [
    # Pydantic
    "pydantic",
    "pydantic_settings",
    "pydantic.deprecated.decorator",

    # Google Gen AI SDK
    "google.generativeai",
    "google.ai.generativelanguage",
    "google.api_core",
    "google.auth",
    "grpc",
    "grpc._cython.cygrpc",

    # Reportlab (PDF-отчёты)
    "reportlab.pdfbase._fontdata_enc_winansi",
    "reportlab.pdfbase._fontdata_enc_macroman",
    "reportlab.pdfbase._fontdata_enc_standard",
    "reportlab.pdfbase._fontdata_enc_symbol",
    "reportlab.pdfbase._fontdata_enc_zapfdingbats",
    "reportlab.pdfbase._fontdata_widths_helvetica",

    # mss
    "mss.windows",

    # pywin32
    "win32gui",
    "win32process",
    "win32api",
    "win32con",

    # pyautogui
    "pyautogui",
    "pyscreeze",
    "pymsgbox",
    "pytweening",
    "mouseinfo",

    # PySide6 — обычно ловится сам, но подстрахуемся
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",

    # HTTP-клиент (GLM, Ollama, скиллы)
    "httpx",

    # Провайдеры LLM (импортируются лениво в фабрике)
    "jarvis.llm.providers.glm",
    "jarvis.llm.providers.gemini",
    "jarvis.llm.providers.ollama_provider",

    # Голос / поиск / хоткей (ленивые импорты)
    "pyttsx3",
    "pyttsx3.drivers",
    "pyttsx3.drivers.sapi5",
    "comtypes",
    "ddgs",
    "keyboard",

    # Голос: распознавание (vosk) и микрофон (sounddevice)
    "vosk",
    "sounddevice",
    "cffi",
    "_cffi_backend",

    # Встроенный сервер для мобильного приложения
    "jarvis.server.api",
    "jarvis.server.embedded",
    "fastapi",
    "starlette.routing",
    "uvicorn",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",
    "websockets.legacy",
    "websockets.legacy.server",
    "qrcode",
]

DATAS = [
    (".env.example", "."),
    # Мобильное PWA-приложение (раздаётся встроенным сервером)
    ("src/jarvis/server/webapp", "jarvis/server/webapp"),
] + collect_data_files("vosk")

# Нативные библиотеки для голоса (libvosk, portaudio)
EXTRA_BINARIES = collect_dynamic_libs("vosk") + collect_dynamic_libs("sounddevice")

a = Analysis(
    ["src/jarvis/gui/__main__.py"],
    pathex=["src"],
    binaries=EXTRA_BINARIES,
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ВАЖНО: НЕ исключаем "test" и "unittest" — это стандартные пакеты Python,
        # без unittest.mock у нас падает reportlab.
        "tkinter",
        "matplotlib",
        "tests",
        "pytest",
        # Не нужны бэкенды Qt, которые мы не используем
        "PySide6.QtNetwork",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.Qt3DCore",
        "PySide6.QtMultimedia",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtPdf",
        "PySide6.QtCharts",
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
    name="Jarvis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,        # КЛЮЧЕВОЕ: True для консоли, False для GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="jarvis.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Jarvis",
)
