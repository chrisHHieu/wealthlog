"""MCP tools for transactions."""

from mcp.server.fastmcp import FastMCP

from app.ai.mcp.tools.transaction_search import register_search_tools
from app.ai.mcp.tools.transaction_writes import register_write_tools


def register(mcp: FastMCP) -> None:
    register_search_tools(mcp)
    register_write_tools(mcp)
