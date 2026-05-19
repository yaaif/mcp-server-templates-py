from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    http_host: str
    port: int
    service_name: str
    service_version: str
    platform_version: str
    mcp_path: str
    mcp_server_name: str
    mcp_server_version: str
    mcp_auth_bearer_token: str
    default_tenant_id: str
    log_level: str
    shutdown_grace_seconds: int
    redact_secrets: bool


def load_settings() -> Settings:
    load_dotenv(".env")

    port = _get_int("PORT", 8096)
    service_name = _get_str("SERVICE_NAME", "template-mcp-service-python")
    service_version = _get_str("SERVICE_VERSION", _get_str("MCP_SERVER_VERSION", "0.1.0"))
    platform_version = _get_str("PLATFORM_VERSION", service_version)

    mcp_path = _normalize_path(_get_str("MCP_PATH", "/mcp"))

    return Settings(
        http_host=_get_str("HTTP_HOST", "0.0.0.0"),
        port=port,
        service_name=service_name,
        service_version=service_version,
        platform_version=platform_version,
        mcp_path=mcp_path,
        mcp_server_name=_get_str("MCP_SERVER_NAME", service_name),
        mcp_server_version=_get_str("MCP_SERVER_VERSION", "0.1.0"),
        mcp_auth_bearer_token=_get_str("MCP_AUTH_BEARER_TOKEN", ""),
        default_tenant_id=_get_str("DEFAULT_TENANT_ID", ""),
        log_level=_get_str("LOG_LEVEL", "INFO").upper(),
        shutdown_grace_seconds=_get_int("SHUTDOWN_GRACE_SECONDS", 10),
        redact_secrets=_get_bool("REDACT_SECRETS", True),
    )


def _first_non_empty(*values: str | None, fallback: str = "") -> str:
    for value in values:
        if value is None:
            continue
        stripped = value.strip()
        if stripped:
            return stripped
    return fallback


def _get_str(key: str, default: str) -> str:
    value = os.getenv(key)
    if value is None:
        return default
    stripped = value.strip()
    return stripped if stripped else default


def _get_int(key: str, default: int) -> int:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key, "").strip().lower()
    if raw in {"1", "true", "yes"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    return default


def _normalize_path(path: str) -> str:
    normalized = path.strip()
    if not normalized:
        normalized = "/mcp"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized
