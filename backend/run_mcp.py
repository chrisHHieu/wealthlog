"""Run the WealthLog MCP server.

Usage:
    uv run python run_mcp.py          # stdio (for Claude Desktop, agents)
    uv run python run_mcp.py --sse    # SSE on port 8002 (for MCP Inspector)
"""

import sys

from app.mcp.server import mcp

if __name__ == "__main__":
    if "--sse" in sys.argv:
        from starlette.applications import Starlette
        from starlette.middleware import Middleware
        from starlette.middleware.cors import CORSMiddleware
        from starlette.routing import Mount

        # Wrap MCP SSE app inside a fresh Starlette app with CORS
        sse_app = mcp.sse_app()
        app = Starlette(
            routes=[Mount("/", app=sse_app)],
            middleware=[
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["*"],
                    allow_headers=["*"],
                ),
            ],
        )

        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8002)
    else:
        mcp.run()
