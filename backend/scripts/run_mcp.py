"""Run the WealthLog MCP server.

Usage:
    uv run python scripts/run_mcp.py          # stdio (for Claude Desktop, agents)
    uv run python scripts/run_mcp.py --sse    # SSE on port 8002 (for MCP Inspector)
"""

import sys

from app.ai.mcp.server import mcp
from app.config import settings

if __name__ == "__main__":
    if "--sse" in sys.argv:
        import uvicorn

        # Reuse the package entrypoint (CORS + bearer auth) so dev and the Docker
        # service run the exact same app.
        from app.ai.mcp.sse import build_sse_app

        uvicorn.run(build_sse_app(), host=settings.mcp_host, port=settings.mcp_port)
    else:
        mcp.run()
