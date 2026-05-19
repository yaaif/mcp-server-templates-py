from __future__ import annotations

import logging

import uvicorn

from .app import create_asgi_app
from .config import load_settings
from .telemetry import setup_telemetry


def configure_logging(level: str) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("template_mcp_server")


def main() -> None:
    settings = load_settings()
    logger = configure_logging(settings.log_level)
    setup_telemetry(settings.service_name, settings.service_version, logger)
    app = create_asgi_app(settings, logger)

    logger.info(
        "starting template mcp server",
        extra={
            "service_name": settings.service_name,
            "http_host": settings.http_host,
            "port": settings.port,
            "mcp_path": settings.mcp_path,
        },
    )

    uvicorn.run(
        app,
        host=settings.http_host,
        port=settings.port,
        timeout_graceful_shutdown=settings.shutdown_grace_seconds,
    )


if __name__ == "__main__":
    main()
