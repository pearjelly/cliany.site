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


def is_safe_session_domain(value: Any) -> bool:
    """Return whether *value* is a host with an optional valid port.

    Session names originate from URL hosts, but the SDK also exposes a direct
    ``save_session(domain)`` method. Keep that path from accepting URL
    credentials or path-like storage identifiers before it opens Chrome.
    """
    if not isinstance(value, str) or not value or any(char.isspace() for char in value):
        return False
    try:
        parsed = urlparse(f"//{value}")
        if (
            not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            return False
        _ = parsed.port
        return True
    except ValueError:
        return False
