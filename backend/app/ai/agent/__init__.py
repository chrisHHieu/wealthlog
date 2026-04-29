"""Agent package — public API.

Submodules:
- ``runner``: main loop (``run_agent_stream``)
- ``prompt``: system prompt builder
- ``compaction``: short-term memory (turn-aware history compaction)
- ``tools``: MCP tool plumbing
- ``streaming``: SSE event names + encoder
"""

from app.ai.agent.runner import run_agent_stream

__all__ = ["run_agent_stream"]
