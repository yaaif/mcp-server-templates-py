from mcp.server.fastmcp import FastMCP

from template_mcp_server.config import Settings
from template_mcp_server.tools import register_tools
from template_mcp_server.tools import template_echo, template_ping


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


def test_register_tools():
    server = FastMCP(name="test")
    register_tools(server, _settings())


def test_template_ping():
    payload = template_ping()
    assert payload["message"] == "pong"


def test_template_echo():
    payload = template_echo("hello")
    assert payload["text"] == "hello"
    assert payload["length"] == 5
