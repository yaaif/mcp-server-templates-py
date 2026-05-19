import logging

from starlette.testclient import TestClient

from template_mcp_server.app import create_asgi_app
from template_mcp_server.config import Settings


def _settings() -> Settings:
    return Settings(
        http_host="0.0.0.0",
        port=8096,
        service_name="template-mcp-service-python",
        service_version="0.1.0",
        platform_version="0.1.0",
        mcp_path="/mcp",
        mcp_server_name="template-mcp-service-python",
        mcp_server_version="0.1.0",
        mcp_auth_bearer_token="",
        default_tenant_id="",
        log_level="INFO",
        shutdown_grace_seconds=10,
        redact_secrets=True,
    )


def test_create_asgi_app_starts_and_healthz():
    app = create_asgi_app(_settings(), logging.getLogger("test.app"))
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["service"] == "template-mcp-service-python"


def test_mcp_paths_do_not_redirect():
    app = create_asgi_app(_settings(), logging.getLogger("test.app"))
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    with TestClient(app, base_url="http://localhost:8096", follow_redirects=False) as client:
        response = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
        assert response.status_code != 307

        response = client.post("/mcp/", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
        assert response.status_code != 307


def test_mcp_delete_is_accepted_for_stateless_transport():
    app = create_asgi_app(_settings(), logging.getLogger("test.app"))

    with TestClient(app, base_url="http://localhost:8096", follow_redirects=False) as client:
        response = client.delete("/mcp")
        assert response.status_code == 200

        response = client.delete("/mcp/")
        assert response.status_code == 200
