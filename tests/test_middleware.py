import logging

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from template_mcp_server.middleware import (
    BearerAuthMiddleware,
    RequestLoggingMiddleware,
    RuntimeCredentialMiddleware,
)


async def ok(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True})


def test_bearer_auth_middleware():
    app = Starlette(routes=[Route("/mcp", ok, methods=["GET"])])
    app.add_middleware(
        BearerAuthMiddleware,
        bearer_token="secret",
        protected_path="/mcp",
        service_name="template-mcp-service-python",
    )

    with TestClient(app) as client:
        unauthorized = client.get("/mcp")
        assert unauthorized.status_code == 401

        invalid = client.get("/mcp", headers={"Authorization": "Bearer wrong"})
        assert invalid.status_code == 401

        valid = client.get("/mcp", headers={"Authorization": "Bearer secret"})
        assert valid.status_code == 200


def test_request_logging_middleware_sets_request_id():
    app = Starlette(routes=[Route("/healthz", ok, methods=["GET"])])
    app.add_middleware(RequestLoggingMiddleware, logger=logging.getLogger("test"))

    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.headers.get("x-request-id")


async def current_runtime_key(_: Request) -> JSONResponse:
    from template_mcp_server.middleware import current_runtime_api_key

    return JSONResponse({"runtime_api_key": current_runtime_api_key()})


def test_runtime_credential_middleware_reads_runtime_header():
    app = Starlette(routes=[Route("/mcp", current_runtime_key, methods=["GET"])])
    app.add_middleware(RuntimeCredentialMiddleware, protected_path="/mcp")

    with TestClient(app) as client:
        response = client.get("/mcp", headers={"X-Runtime-API-Key": "mapped-api-key"})
        assert response.status_code == 200
        assert response.json()["runtime_api_key"] == "mapped-api-key"


def test_runtime_credential_middleware_is_path_scoped():
    app = Starlette(
        routes=[
            Route("/mcp", current_runtime_key, methods=["GET"]),
            Route("/healthz", current_runtime_key, methods=["GET"]),
        ]
    )
    app.add_middleware(RuntimeCredentialMiddleware, protected_path="/mcp")

    with TestClient(app) as client:
        inside = client.get("/mcp", headers={"X-Runtime-API-Key": "scoped-key"})
        assert inside.status_code == 200
        assert inside.json()["runtime_api_key"] == "scoped-key"

        outside = client.get("/healthz", headers={"X-Runtime-API-Key": "ignored-key"})
        assert outside.status_code == 200
        assert outside.json()["runtime_api_key"] == ""

