"""Standalone SSE entrypoint for the WealthLog MCP server (CORS + bearer auth).

Run it with::

    uv run uvicorn app.ai.mcp.sse:app --host 0.0.0.0 --port 8002

Lives in the app package (not ``scripts/``) so it ships in the Docker image and
can run as its own service — the WealthLog half of the eventual Chip split.
"""

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from app.ai.mcp.auth import BearerAuthMiddleware
from app.ai.mcp.server import mcp
from app.config import settings


def build_sse_app() -> Starlette:
    """The MCP SSE app wrapped with CORS and (optional) bearer auth."""
    return Starlette(
        routes=[Mount("/", app=mcp.sse_app())],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"],
            ),
            Middleware(BearerAuthMiddleware, token=settings.mcp_auth_token),
        ],
    )


app = build_sse_app()
