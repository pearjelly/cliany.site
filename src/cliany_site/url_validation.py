"""Shared URL validation for browser-facing public entry points."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def is_safe_http_url(value: Any) -> bool:
    """Return whether *value* is a whitespace-free HTTP(S) URL with a host."""
    if not isinstance(value, str) or any(char.isspace() for char in value):
        return False
    try:
        parsed = urlparse(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return False
        _ = parsed.port
        return True
    except ValueError:
        return False
