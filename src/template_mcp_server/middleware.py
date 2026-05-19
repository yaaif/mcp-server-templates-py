from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .telemetry import current_trace_ids, start_span

_runtime_api_key: ContextVar[str] = ContextVar("template_runtime_api_key", default="")


def current_runtime_api_key() -> str:
    """Returns a per-request API key forwarded by agent-service (if any)."""
    return _runtime_api_key.get()


def _first_non_empty_header_value(request: Request, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = (request.headers.get(key) or "").strip()
        if value:
            return value
    return ""


class RuntimeCredentialMiddleware(BaseHTTPMiddleware):
    """Captures runtime credentials from platform headers on the MCP path only.

    Customize RUNTIME_CREDENTIAL_HEADERS when creating a service that needs
    per-request API keys (for example LLM providers).
    """

    RUNTIME_CREDENTIAL_HEADERS: tuple[str, ...] = (
        "X-Runtime-API-Key",
        "X-API-Key",
    )

    def __init__(self, app, protected_path: str) -> None:
        super().__init__(app)
        self._path = protected_path

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not (path == self._path or path.startswith(f"{self._path}/")):
            return await call_next(request)

        runtime_key = _first_non_empty_header_value(request, self.RUNTIME_CREDENTIAL_HEADERS)
        token = _runtime_api_key.set(runtime_key)
        try:
            return await call_next(request)
        finally:
            _runtime_api_key.reset(token)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger: logging.Logger) -> None:
        super().__init__(app)
        self._logger = logger

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or request.headers.get("x-correlation-id") or f"req-{uuid.uuid4().hex[:12]}"
        start = time.perf_counter()
        with start_span(
            "template.http.request",
            {
                "http.method": request.method,
                "http.target": request.url.path,
                "request.id": request_id,
            },
        ):
            response = await call_next(request)

        duration_ms = int((time.perf_counter() - start) * 1000)
        trace_id, span_id = current_trace_ids()
        self._logger.info(
            "http request completed",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "remote_addr": request.client.host if request.client else "",
            },
        )
        response.headers["x-request-id"] = request_id
        return response


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, bearer_token: str, protected_path: str, service_name: str) -> None:
        super().__init__(app)
        self._token = (bearer_token or "").strip()
        self._path = protected_path
        self._service_name = service_name

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self._token:
            return await call_next(request)

        path = request.url.path
        if not (path == self._path or path.startswith(f"{self._path}/")):
            return await call_next(request)

        auth = request.headers.get("authorization", "").strip()
        if not auth.lower().startswith("bearer "):
            return JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": f'Bearer realm="{self._service_name}"'},
            )

        provided = auth[7:].strip()
        if provided != self._token:
            return JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": f'Bearer realm="{self._service_name}"'},
            )

        return await call_next(request)
