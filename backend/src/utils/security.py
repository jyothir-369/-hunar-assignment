"""HMAC signature validation for incoming Hunar webhooks."""

import base64
import hashlib
import hmac

from src.config import settings


def compute_signature(timestamp: str, body: bytes) -> str:
    """Compute the base64-encoded HMAC-SHA256 signature for a webhook payload."""
    secret = settings.HUNAR_WEBHOOK_SECRET.encode("utf-8")
    message = f"{timestamp}.".encode("utf-8") + body
    digest = hmac.new(secret, message, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def validate_signature(timestamp: str, body: bytes, signature: str) -> bool:
    """Return True if the signature matches the expected HMAC for the given body.

    If HUNAR_WEBHOOK_SECRET is not configured, validation is bypassed (development only).
    """
    if not settings.HUNAR_WEBHOOK_SECRET:
        return True
    if not signature or not timestamp:
        return False
    expected = compute_signature(timestamp, body)
    return hmac.compare_digest(signature, expected)
