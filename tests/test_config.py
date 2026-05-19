from template_mcp_server.config import load_settings


def test_load_settings_defaults(monkeypatch):
    monkeypatch.delenv("HTTP_HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("MCP_PATH", raising=False)

    settings = load_settings()

    assert settings.http_host == "0.0.0.0"
    assert settings.port == 8096
    assert settings.mcp_path == "/mcp"


def test_load_settings_override(monkeypatch):
    monkeypatch.setenv("HTTP_HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9100")
    monkeypatch.setenv("MCP_PATH", "custom-mcp")

    settings = load_settings()

    assert settings.http_host == "127.0.0.1"
    assert settings.port == 9100
    assert settings.mcp_path == "/custom-mcp"

