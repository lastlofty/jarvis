"""python -m jarvis.main — запускает FastAPI сервер."""
from __future__ import annotations

from jarvis.server.api import run


if __name__ == "__main__":
    run()
