"""FastAPI-сервер: REST + WebSocket точка входа для мобильного приложения."""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jarvis.bootstrap import load_extensions, start_mcp, stop_mcp
from jarvis.core.config import settings
from jarvis.core.logging_setup import logger, setup_logging
from jarvis.executor import comm_tools, input_tools
from jarvis.llm.orchestrator import Orchestrator
from jarvis.observer.observer import observer
from jarvis.server import security


# ---------- Lifespan ----------


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Jarvis starting up...")
    security.warn_if_weak()
    load_extensions()
    await start_mcp()
    if settings.enable_observer:
        observer.start()
    app.state.clients = ConnectionManager()
    comm_tools.bridge.set_send_callback(app.state.clients.broadcast)
    # Оркестратор создаётся лениво при первой команде — иначе сервер
    # не сможет даже отдать /health, если ключ модели не задан.
    app.state.orchestrator = None
    yield
    logger.info("Jarvis shutting down...")
    observer.stop()
    await stop_mcp()


def _get_orchestrator() -> Orchestrator:
    if app.state.orchestrator is None:
        app.state.orchestrator = Orchestrator()
    return app.state.orchestrator


app = FastAPI(title="Jarvis Agent", version="0.2.0", lifespan=lifespan)


# ---------- Мобильное веб-приложение (PWA) ----------
_WEBAPP_DIR = Path(__file__).parent / "webapp"
if _WEBAPP_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(_WEBAPP_DIR), html=True), name="webapp")


@app.get("/")
async def _root() -> RedirectResponse:
    """Корень → мобильное приложение."""
    return RedirectResponse(url="/app/")


# ---------- Auth ----------


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def verify_token(
    request: Request, authorization: str | None = Header(default=None)
) -> None:
    """Проверка Bearer-токена: constant-time + анти-брутфорс по IP."""
    ip = _client_ip(request)

    remaining = security.lock_remaining(ip)
    if remaining > 0:
        raise HTTPException(429, f"Слишком много попыток. Подождите {int(remaining)} c.")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Требуется заголовок Authorization: Bearer <token>")

    token = authorization.removeprefix("Bearer ").strip()
    if not security.check_token(token):
        security.record_fail(ip)
        raise HTTPException(403, "Неверный токен")
    security.record_success(ip)


# ---------- Connection manager ----------


class ConnectionManager:
    """Хранит активные WS-соединения и умеет рассылать сообщения."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        logger.info(f"WS клиент подключён ({len(self._connections)} активных)")

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)
        logger.info(f"WS клиент отключён ({len(self._connections)} активных)")

    async def broadcast(self, payload: dict[str, Any]) -> None:
        text = json.dumps(payload, ensure_ascii=False)
        async with self._lock:
            dead: list[WebSocket] = []
            for ws in self._connections:
                try:
                    await ws.send_text(text)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.discard(ws)


# ---------- REST ----------


class CommandIn(BaseModel):
    text: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.post("/command", dependencies=[Depends(verify_token)])
async def command(payload: CommandIn) -> dict[str, str]:
    orch = _get_orchestrator()
    answer = await orch.handle(payload.text)
    return {"answer": answer}


@app.get("/screenshot", dependencies=[Depends(verify_token)])
async def screenshot() -> FileResponse:
    """Свежий скриншот всех мониторов."""
    result = await asyncio.to_thread(input_tools.take_screenshot)
    if result.status != "success" or not result.data:
        return JSONResponse({"error": result.message}, status_code=500)
    path = Path(result.data["path"])
    return FileResponse(path, media_type="image/png", filename=path.name)


# ---------- WebSocket ----------


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Двусторонний канал для мобильного приложения.

    Авторизация: первый кадр должен быть {"type":"auth", "token":"..."}.
    """
    clients: ConnectionManager = app.state.clients
    orch = _get_orchestrator()

    ip = ws.client.host if ws.client else "unknown"
    await ws.accept()
    try:
        # 0) Анти-брутфорс
        if security.lock_remaining(ip) > 0:
            await ws.send_text(json.dumps({"type": "auth", "ok": False, "error": "rate_limited"}))
            await ws.close(code=4429)
            return

        # 1) Auth
        try:
            first = await asyncio.wait_for(ws.receive_text(), timeout=10.0)
        except asyncio.TimeoutError:
            await ws.close(code=4401)
            return
        try:
            msg = json.loads(first)
        except json.JSONDecodeError:
            await ws.close(code=4400)
            return
        if msg.get("type") != "auth" or not security.check_token(msg.get("token")):
            security.record_fail(ip)
            await ws.send_text(json.dumps({"type": "auth", "ok": False}))
            await ws.close(code=4403)
            return
        security.record_success(ip)
        await ws.send_text(json.dumps({"type": "auth", "ok": True}))

        # 2) Регистрируем как broadcast-получателя
        async with clients._lock:
            clients._connections.add(ws)

        # 3) Цикл сообщений
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"type": "error", "message": "bad json"}))
                continue

            mtype = data.get("type")
            if mtype == "command":
                await ws.send_text(
                    json.dumps({"type": "status", "status": "in_progress"})
                )
                answer = await orch.handle(data.get("text", ""))
                await ws.send_text(
                    json.dumps(
                        {"type": "status", "status": "done", "message": answer},
                        ensure_ascii=False,
                    )
                )
            elif mtype == "answer":
                # Ответ на ask_user
                qid = int(data.get("id", 0))
                ans = str(data.get("answer", ""))
                comm_tools.bridge.resolve(qid, ans)
            elif mtype == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
            else:
                await ws.send_text(
                    json.dumps({"type": "error", "message": f"unknown type {mtype}"})
                )
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception(f"WS error: {e}")
    finally:
        await clients.disconnect(ws)


def run() -> None:
    """Точка входа `python -m jarvis.server.api` или скрипта main."""
    import uvicorn

    uvicorn.run(
        "jarvis.server.api:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    run()
