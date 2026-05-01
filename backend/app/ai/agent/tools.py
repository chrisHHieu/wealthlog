"""MCP tool plumbing for the agent — discovery + execution."""

from app.ai.mcp.server import mcp
from app.logging_config import get_logger

logger = get_logger(__name__)

# Max tool-call iterations per agent turn, to prevent infinite loops.
MAX_ITERATIONS = 15


async def get_tools_for_claude() -> list[dict]:
    """Convert MCP tools to Anthropic tool format."""
    mcp_tools = await mcp.list_tools()
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema,
        }
        for t in mcp_tools
    ]


async def execute_tool(name: str, arguments: dict) -> tuple[str, bool]:
    """Execute an MCP tool; return (text, is_error).

    is_error=True signals the Claude API that the result is an error, allowing
    the model to decide whether to retry or surface it to the user.
    """
    try:
        result = await mcp.call_tool(name, arguments)
        # call_tool returns (list[TextContent], dict) or similar
        contents = result[0] if isinstance(result, tuple) else result

        texts: list[str] = []
        if isinstance(contents, list):
            for item in contents:
                if hasattr(item, "text"):
                    texts.append(item.text)
                elif isinstance(item, str):
                    texts.append(item)
        elif isinstance(contents, str):
            texts.append(contents)

        return "\n".join(texts) if texts else "No results.", False
    except Exception as e:
        logger.exception("Tool execution error: %s", name)
        return f"Tool error ({name}): {e}", True
