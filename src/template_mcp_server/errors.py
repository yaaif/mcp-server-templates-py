from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolErrorCode:
    INVALID_INPUT: str = "INVALID_INPUT"
    UPSTREAM_ERROR: str = "UPSTREAM_ERROR"
    NOT_FOUND: str = "NOT_FOUND"
    INTERNAL_ERROR: str = "INTERNAL_ERROR"


ERROR_CODES = ToolErrorCode()


class ToolError(Exception):
    """Structured tool error with a stable code for MCP clients."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


def ensure(condition: bool, code: str, message: str, details: dict[str, Any] | None = None) -> None:
    if not condition:
        raise ToolError(code=code, message=message, details=details)
