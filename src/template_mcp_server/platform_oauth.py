"""Optional OAuth2 client-credentials (JWT bearer) for outbound HTTP to YAAIF core services."""

from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def _split_audience_list(raw: str) -> list[str]:
    s = raw.strip()
    if not s:
        return []
    parts: list[str] = []
    for chunk in re.split(r"[,;]", s):
        c = chunk.strip()
        if c:
            parts.append(c)
    return parts


def _normalize_oauth_scope_from_audience(aud: str) -> str:
    s = aud.strip()
    if not s:
        return ""
    if _UUID_RE.match(s):
        return f"api://{s.lower()}/.default"
    lower = s.lower()
    if lower.startswith("api://"):
        s = s.rstrip("/")
        lower = s.lower()
        if lower.endswith("/.default"):
            return s
        return s + "/.default"
    return s


def _scopes_from_jwt_audience(jwt_audience: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for part in _split_audience_list(jwt_audience):
        sc = _normalize_oauth_scope_from_audience(part)
        if not sc:
            continue
        key = sc.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(sc)
    return out


class PlatformOAuthTokenCache:
    """Thread-safe cached bearer from YAAIF_PLATFORM_S2S_OAUTH_* (stdlib only)."""

    def __init__(
        self,
        getenv: Callable[[str], str | None] | None = None,
        jwt_audience: str | None = None,
    ) -> None:
        self._getenv = getenv or os.getenv
        self._jwt_audience = (
            (jwt_audience or "").strip()
            if jwt_audience is not None
            else (self._getenv("AUTH_JWT_AUDIENCE") or "").strip()
        )
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expiry_epoch: float = 0.0

    def configured(self) -> bool:
        return bool((self._getenv("YAAIF_PLATFORM_S2S_OAUTH_TOKEN_URL") or "").strip())

    def bearer(self) -> str | None:
        if not self.configured():
            return None
        scopes = _scopes_from_jwt_audience(self._jwt_audience)
        if not scopes:
            raise RuntimeError(
                "AUTH_JWT_AUDIENCE must be set (non-empty) when YAAIF_PLATFORM_S2S_OAUTH_TOKEN_URL is set"
            )
        now = time.time()
        with self._lock:
            if self._token and now < self._expiry_epoch - 60:
                return self._token
            token, expires_in = self._fetch_token(scopes)
            self._token = token
            self._expiry_epoch = now + float(expires_in if expires_in > 0 else 3600)
            return self._token

    def _fetch_token(self, scopes: list[str]) -> tuple[str, float]:
        token_url = (self._getenv("YAAIF_PLATFORM_S2S_OAUTH_TOKEN_URL") or "").strip()
        cid = (self._getenv("YAAIF_PLATFORM_S2S_OAUTH_CLIENT_ID") or "").strip()
        secret = (self._getenv("YAAIF_PLATFORM_S2S_OAUTH_CLIENT_SECRET") or "").strip()
        missing = [k for k, v in [
            ("YAAIF_PLATFORM_S2S_OAUTH_TOKEN_URL", token_url),
            ("YAAIF_PLATFORM_S2S_OAUTH_CLIENT_ID", cid),
            ("YAAIF_PLATFORM_S2S_OAUTH_CLIENT_SECRET", secret),
        ] if not v]
        if missing:
            raise RuntimeError("platform OAuth not fully configured: " + ", ".join(missing))
        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": cid,
                "client_secret": secret,
                "scope": " ".join(scopes),
            }
        ).encode()
        req = urllib.request.Request(
            token_url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            raise RuntimeError(f"OAuth token HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"OAuth token request failed: {e}") from e
        data: dict[str, Any] = json.loads(raw.decode())
        access = (data.get("access_token") or "").strip()
        if not access:
            raise RuntimeError("OAuth token response missing access_token")
        expires_in = float(data.get("expires_in") or 3600)
        return access, expires_in
