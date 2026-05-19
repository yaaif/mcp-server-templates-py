from __future__ import annotations

from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from .config import Settings
from .telemetry import start_span


def template_ping(message: str = "pong", include_timestamp: bool = False) -> dict:
    payload: dict[str, object] = {"message": message}
    if include_timestamp:
        payload["timestamp"] = datetime.now(tz=timezone.utc).isoformat()
    now = datetime.now(tz=timezone.utc)
    payload["_server_date"] = now.date().isoformat()
    payload["_server_weekday"] = now.strftime("%A")
    return payload


def template_echo(text: str) -> dict:
    return {
        "text": text,
        "length": len(text),
    }


def register_tools(server: FastMCP, settings: Settings) -> None:
    _ = settings

    def traced_template_ping(message: str = "pong", include_timestamp: bool = False) -> dict:
        with start_span(
            "template.tool.execute",
            {"mcp.tool.name": "template_ping"},
        ):
            return template_ping(message=message, include_timestamp=include_timestamp)

    def traced_template_echo(text: str) -> dict:
        with start_span(
            "template.tool.execute",
            {"mcp.tool.name": "template_echo"},
        ):
            return template_echo(text=text)

    server.tool(
        name="template_ping",
        description="Basic connectivity and heartbeat-style check.",
    )(traced_template_ping)
    server.tool(
        name="template_echo",
        description="Echo back the provided text.",
    )(traced_template_echo)
