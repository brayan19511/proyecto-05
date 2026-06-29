"""Small, security-focused helpers for audit persistence."""

from collections.abc import Mapping
from typing import Any


SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "password",
    "password_hash",
    "refresh_token",
    "secret",
    "set-cookie",
    "token",
    "access_token",
    "api_key",
    "x-api-key",
}

AUDIT_HEADER_ALLOWLIST = {
    "content-type",
    "user-agent",
    "x-forwarded-for",
    "x-request-id",
}


def sanitize_payload(value: Any) -> Any:
    """Redact known secrets recursively while preserving diagnostic structure."""
    if isinstance(value, Mapping):
        return {
            key: (
                "[REDACTED]"
                if str(key).lower() in SENSITIVE_KEYS
                else sanitize_payload(item)
            )
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]

    return value


def sanitize_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Store only headers with diagnostic value; authentication is excluded."""
    return {
        key: value
        for key, value in headers.items()
        if key.lower() in AUDIT_HEADER_ALLOWLIST
    }
