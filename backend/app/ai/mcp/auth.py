"""Bearer-token auth for the MCP SSE server.

A pure-ASGI middleware (not BaseHTTPMiddleware) so it never buffers the SSE
stream. When the configured token is empty it's a no-op (dev/local); when set,
every HTTP request must carry ``Authorization: Bearer <token>`` or gets 401.
"""

from collections.abc import Awaitable, Callable

Scope = dict
Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]


class BearerAuthMiddleware:
    def __init__(self, app: Callable, token: str = "") -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.token and scope.get("type") == "http":
            headers = dict(scope.get("headers") or [])
            provided = headers.get(b"authorization", b"").decode()
            if provided != f"Bearer {self.token}":
                await self._reject(send)
                return
        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"Unauthorized"})
