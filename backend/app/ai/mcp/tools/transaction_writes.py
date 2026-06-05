"""Write MCP tool registration for transactions."""

from mcp.server.fastmcp import FastMCP

from app.ai.mcp.tools.transaction_create import register_create_tools
from app.ai.mcp.tools.transaction_mutations import register_mutation_tools


def register_write_tools(mcp: FastMCP) -> None:
    register_create_tools(mcp)
    register_mutation_tools(mcp)
