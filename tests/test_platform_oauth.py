from template_mcp_server.platform_oauth import (
    PlatformOAuthTokenCache,
    _scopes_from_jwt_audience,
)


def test_scopes_uuid_normalized():
    guid = "b9b79b20-5398-4655-b834-b232b45b268a"
    assert _scopes_from_jwt_audience(guid) == [f"api://{guid}/.default"]


def test_optional_oauth_not_configured():
    c = PlatformOAuthTokenCache(getenv=lambda _k: "")
    assert c.configured() is False
    assert c.bearer() is None
