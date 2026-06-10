"""Клиент внешних MCP-серверов (stdio-транспорт).

Читает mcp_servers.json вида:

    {
      "servers": [
        {"name": "filesystem", "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:/work"]}
      ]
    }

Для каждого сервера поднимает сессию, получает список инструментов и
регистрирует их в общем реестре Jarvis с префиксом mcp_<server>_<tool>.

Пакет `mcp` опционален: если не установлен или mcp_enabled=false — тихо пропускаем.
"""
from __future__ import annotations

import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from jarvis.core.config import settings
from jarvis.core.logging_setup import logger
from jarvis.core.types import ToolResult
from jarvis.executor import registry


class MCPManager:
    """Держит активные сессии к MCP-серверам и проксирует их инструменты."""

    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None
        self._sessions: dict[str, Any] = {}
        self.connected_tools: list[str] = []

    def _read_config(self) -> list[dict[str, Any]]:
        path = Path(settings.mcp_config_path)
        if not path.exists():
            logger.info(f"MCP: конфиг не найден ({path}) — пропускаю")
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("servers", [])
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"MCP: ошибка чтения конфига: {e}")
            return []

    async def start(self) -> None:
        """Подключается ко всем серверам из конфига (если включено)."""
        if not settings.mcp_enabled:
            return
        servers = self._read_config()
        if not servers:
            return

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            logger.warning(
                "MCP включён, но пакет `mcp` не установлен. "
                "Установите: pip install mcp"
            )
            return

        self._stack = AsyncExitStack()
        for srv in servers:
            name = srv.get("name", "server")
            try:
                params = StdioServerParameters(
                    command=srv["command"],
                    args=srv.get("args", []),
                    env=srv.get("env"),
                )
                read, write = await self._stack.enter_async_context(stdio_client(params))
                session = await self._stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                self._sessions[name] = session
                await self._register_server_tools(name, session)
            except Exception as e:  # noqa: BLE001
                logger.error(f"MCP сервер {name}: не удалось подключиться — {e}")

    async def _register_server_tools(self, server: str, session: Any) -> None:
        tools = await session.list_tools()
        for tool in tools.tools:
            full_name = f"mcp_{server}_{tool.name}"
            declaration = {
                "name": full_name,
                "description": f"[MCP:{server}] {tool.description or tool.name}",
                "parameters": tool.inputSchema or {"type": "object", "properties": {}},
            }
            handler = self._make_handler(server, tool.name)
            registry.register_tool(declaration, handler)
            self.connected_tools.append(full_name)
        logger.info(f"MCP сервер {server}: подключено инструментов {len(tools.tools)}")

    def _make_handler(self, server: str, tool_name: str):
        async def _handler(**kwargs: Any) -> ToolResult:
            session = self._sessions.get(server)
            if session is None:
                return ToolResult.fail(f"MCP сервер {server} не подключён")
            try:
                result = await session.call_tool(tool_name, kwargs)
                texts = [
                    getattr(c, "text", "")
                    for c in getattr(result, "content", [])
                    if getattr(c, "text", None)
                ]
                return ToolResult.ok("\n".join(texts) or "(пустой ответ MCP)")
            except Exception as e:  # noqa: BLE001
                return ToolResult.fail(f"MCP {server}.{tool_name}: {e}")

        return _handler

    async def stop(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._sessions.clear()


# Singleton
mcp_manager = MCPManager()
