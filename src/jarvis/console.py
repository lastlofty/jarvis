"""Консольный REPL — пишешь команды в терминал, агент их выполняет.

Для отладки без мобильного приложения. Запуск:
    python -m jarvis.console
"""
from __future__ import annotations

import asyncio

from jarvis.bootstrap import load_extensions, start_mcp, stop_mcp
from jarvis.core.logging_setup import setup_logging
from jarvis.llm.orchestrator import Orchestrator
from jarvis.observer.observer import observer
from jarvis.core.config import settings


async def main() -> None:
    setup_logging()
    load_extensions()
    await start_mcp()
    if settings.enable_observer:
        observer.start()
    orch = Orchestrator()
    print(f"Jarvis консоль · модель: {orch.provider_name}")
    print("Введите команду, 'exit' для выхода.\n")
    try:
        while True:
            try:
                text = await asyncio.to_thread(input, "Вы: ")
            except (EOFError, KeyboardInterrupt):
                break
            if text.strip().lower() in {"exit", "quit", ":q"}:
                break
            print("\nJarvis: ", end="", flush=True)

            def on_chunk(chunk: str) -> None:
                print(chunk, end="", flush=True)

            await orch.handle_stream(text, on_chunk)
            print("\n")
    finally:
        observer.stop()
        await stop_mcp()


if __name__ == "__main__":
    asyncio.run(main())
