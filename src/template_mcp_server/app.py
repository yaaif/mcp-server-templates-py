from __future__ import annotations

import logging
from contextlib import AsyncExitStack, asynccontextmanager

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from .config import Settings
from .middleware import BearerAuthMiddleware, RequestLoggingMiddleware, RuntimeCredentialMiddleware
from .tools import register_tools


class _MCPHTTPPathAdapter:
    """Rewrites mounted MCP paths to / so Streamable HTTP works without 307 redirects."""

    def __init__(self, app, stateless_http: bool) -> None:
        self._app = app
        self._stateless_http = stateless_http

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        # Stateless transports do not maintain MCP sessions; accept DELETE as no-op.
        if self._stateless_http and scope["method"] == "DELETE":
            response = Response(status_code=200, media_type="application/json")
            await response(scope, receive, send)
            return

        rewritten_scope = dict(scope)
        rewritten_scope["path"] = "/"
        rewritten_scope["raw_path"] = b"/"
        await self._app(rewritten_scope, receive, send)


def _mcp_routes(mcp_path: str, endpoint: _MCPHTTPPathAdapter) -> list[Route]:
    methods = ["GET", "POST", "DELETE", "OPTIONS"]
    routes = [Route(mcp_path, endpoint=endpoint, methods=methods)]
    if mcp_path != "/":
        routes.append(Route(f"{mcp_path}/", endpoint=endpoint, methods=methods))
    return routes


def create_mcp_server(settings: Settings) -> FastMCP:
    mcp = FastMCP(
        name=settings.mcp_server_name,
        stateless_http=True,
        json_response=True,
    )
    mcp.settings.streamable_http_path = "/"
    register_tools(mcp, settings)
    return mcp


def create_asgi_app(settings: Settings, logger: logging.Logger) -> Starlette:
    mcp = create_mcp_server(settings)
    mcp_http_app = mcp.streamable_http_app()
    mcp_endpoint = _MCPHTTPPathAdapter(mcp_http_app, stateless_http=mcp.settings.stateless_http)

    async def healthz(_: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": settings.service_name,
                "service_version": settings.service_version,
                "platform_version": settings.platform_version,
            }
        )

    @asynccontextmanager
    async def lifespan(_: Starlette):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(mcp_http_app.router.lifespan_context(mcp_http_app))
            yield

    app = Starlette(
        debug=False,
        routes=[
            Route("/healthz", healthz, methods=["GET"]),
            *_mcp_routes(settings.mcp_path, mcp_endpoint),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(RequestLoggingMiddleware, logger=logger)
    app.add_middleware(RuntimeCredentialMiddleware, protected_path=settings.mcp_path)
    app.add_middleware(
        BearerAuthMiddleware,
        bearer_token=settings.mcp_auth_bearer_token,
        protected_path=settings.mcp_path,
        service_name=settings.service_name,
    )
    return app
