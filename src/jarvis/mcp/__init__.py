"""MCP-клиент Jarvis: подключение к внешним MCP-серверам как клиент.

Опциональная часть (по умолчанию выключена). Требует пакет `mcp` и работает
только если включён mcp_enabled и есть конфиг mcp_servers.json.
"""
from __future__ import annotations

from jarvis.mcp.client import MCPManager, mcp_manager

__all__ = ["MCPManager", "mcp_manager"]
