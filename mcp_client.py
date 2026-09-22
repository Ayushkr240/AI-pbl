"""Connect the LangGraph agent to the local Gmail and Calendar MCP servers."""

import sys

from langchain_mcp_adapters.client import MultiServerMCPClient

SERVER_CONFIG = {
    "email": {
        "command": sys.executable,
        "args": ["email_server.py"],
        "transport": "stdio",
    },
    "calendar": {
        "command": sys.executable,
        "args": ["calendar_server.py"],
        "transport": "stdio",
    },
}

_client = MultiServerMCPClient(SERVER_CONFIG)


async def get_mcp_tools():
    """Fetch tools from every configured MCP server."""
    return await _client.get_tools()
