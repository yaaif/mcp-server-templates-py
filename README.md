# YAAIF MCP Server Template (Python)

Reusable Python scaffold for creating MCP servers on the [YAAIF platform](https://github.com/yaaif/yaaif-platform) using the official MCP Python SDK.

Clone this repository when starting a new Python MCP service, then rename the package and tools for your domain.

## Features

- `mcp` (`FastMCP`) with Streamable HTTP
- Starlette ASGI app with explicit MCP path routing (no 307 redirects)
- `GET /healthz`
- Optional bearer auth for `/mcp`
- Runtime credential middleware (customize header names per service)
- Request logging + OpenTelemetry spans
- Structured tool errors (`errors.py`)

## Project layout

```text
src/template_mcp_server/
tests/
```

## Quick start

```bash
git clone https://github.com/yaaif/mcp-server-templates-py.git my-mcp-service
cd my-mcp-service
cp .env.example .env
uv sync
uv run template-mcp-server
```

Server defaults:

- HTTP address: `0.0.0.0:8096`
- MCP endpoint: `http://localhost:8096/mcp`
- Health endpoint: `http://localhost:8096/healthz`

## Tests

```bash
uv sync --extra dev
uv run python -m pytest
```

## Create a new service

1. Clone this repo.
2. Rename `template_mcp_server` and the console script in `pyproject.toml`.
3. Replace sample tools in `src/template_mcp_server/tools.py`.
4. Extend `config.py` and `.env.example` for your domain.
5. Customize `RuntimeCredentialMiddleware.RUNTIME_CREDENTIAL_HEADERS` if you need per-request API keys.

## MCP routing

The template uses an explicit path adapter so `/mcp` and `/mcp/` work without HTTP 307 redirects, and stateless `DELETE` returns `200`.

For stdio/desktop MCP servers, see `sap-gui-mcp-service` in yaaif-platform.

## Docker

```bash
docker build -t template-mcp-service-python:local .
docker run --rm -p 8096:8096 --env-file ./.env template-mcp-service-python:local
```
