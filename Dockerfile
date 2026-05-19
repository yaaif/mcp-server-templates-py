FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /usr/local /usr/local
COPY .env.example ./

EXPOSE 8096

ENTRYPOINT ["template-mcp-server"]

