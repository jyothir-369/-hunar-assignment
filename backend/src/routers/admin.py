"""Admin endpoints — guarded by a shared secret.

These endpoints are intentionally limited to seed/restart flows that an
operator (or the Settings page's "Re-seed demo data" button) may need to
trigger without shell access to the host. Every route requires the
``X-Admin-Token`` header to match the ``ADMIN_TOKEN`` environment variable.

If ``ADMIN_TOKEN`` is unset, the endpoint is disabled (returns 503) — we
refuse to fall back to a default token because that would be a backdoor
in production.
"""

from __future__ import annotations

import io
import logging
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# Make `scripts/` importable when this router runs in a Railway-style
# environment where the working directory is /app. The seed script needs
# its BACKEND_ROOT on sys.path so its own `from src…` imports resolve.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _BACKEND_ROOT / "scripts"
for p in (str(_BACKEND_ROOT), str(_SCRIPTS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


def _check_admin_token(x_admin_token: str | None) -> None:
    """Verify the request carries a valid admin token.

    Raises 503 if the server is not configured with an ADMIN_TOKEN, and
    401 if the caller's token doesn't match. Both responses are
    deliberately non-specific so they don't leak whether the env var is set.
    """
    expected = ""
    try:
        from src.config import settings as _settings  # local import to avoid cycles

        expected = getattr(_settings, "ADMIN_TOKEN", "") or ""
    except Exception:  # pragma: no cover - defensive
        expected = ""

    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints disabled: ADMIN_TOKEN is not set on the server.",
        )
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Token header.",
        )


@router.post("/seed-demo", status_code=status.HTTP_200_OK)
def seed_demo(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, Any]:
    """Idempotently populate the DB with demo data.

    The underlying script short-circuits when the ``Demo Recruiter Agent``
    marker is already present, so this is safe to call repeatedly. Returns
    a short summary plus the captured stdout/stderr from the seed run.
    """
    _check_admin_token(x_admin_token)

    try:
        from scripts import seed_demo_data  # type: ignore
    except Exception as exc:
        logger.exception("Failed to import seed_demo_data")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not load seed script: {type(exc).__name__}: {exc}",
        ) from exc

    out_buf = io.StringIO()
    err_buf = io.StringIO()
    try:
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            seed_demo_data.main()
    except Exception as exc:
        logger.exception("seed_demo_data.main() raised")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": f"Seed script raised: {type(exc).__name__}: {exc}",
                "stdout": out_buf.getvalue(),
                "stderr": err_buf.getvalue(),
            },
        ) from exc

    return {
        "ok": True,
        "stdout": out_buf.getvalue(),
        "stderr": err_buf.getvalue(),
    }
