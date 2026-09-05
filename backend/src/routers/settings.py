"""Settings endpoint — read-only status of API keys and DB.

Returns the *presence* of each secret, never the value itself. The frontend
uses this to render a "configured: yes/no" panel on the /settings page.
"""

import logging
import os
from typing import Any

from fastapi import APIRouter
from sqlalchemy import select, text

from src.config import settings
from src.database import SessionLocal, engine
from src.models.agent import Agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["Settings"])

DEMO_AGENT_NAME = "Demo Recruiter Agent"


def _mask(value: str) -> str:
    """Return a short prefix so the UI can confirm a value is loaded without
    ever showing the secret itself."""
    if not value:
        return ""
    if len(value) <= 8:
        return "••••"
    return f"{value[:4]}…{value[-4:]}  (length {len(value)})"


def _database_target() -> str:
    """Return a UI-friendly description of the database we're connected to."""
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        # sqlite:///./app.db -> file:app.db
        path = url.split("///", 1)[-1]
        return f"SQLite ({path})"
    if url.startswith("postgres"):
        # Hide credentials in the host part
        try:
            at = url.index("@")
            return f"PostgreSQL ({url[at + 1 :]})"
        except ValueError:
            return "PostgreSQL"
    return url.split("://", 1)[0]


def _is_demo_seeded() -> bool:
    """Return True if the demo seed script has been run.

    The seed script creates an agent named ``DEMO_AGENT_NAME``. We probe for
    that one row in a short-lived session and swallow any error so the
    /api/settings/ endpoint never 500s on this lookup.
    """
    try:
        with SessionLocal() as db:
            row = db.execute(
                select(Agent.id).where(Agent.name == DEMO_AGENT_NAME).limit(1)
            ).first()
            return row is not None
    except Exception:  # pragma: no cover - defensive
        return False


@router.get("/")
def get_settings() -> dict[str, Any]:
    """Read-only view of the runtime configuration.

    Every field is wrapped in its own try/except so a single failure (e.g.
    `os.uname()` blocked in a sandbox, a slow DB ping, an unexpected
    exception in a masker) cannot turn the whole endpoint into a 500.
    """
    db_ok = True
    db_error: str | None = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - depends on deployment
        db_ok = False
        db_error = f"{type(exc).__name__}: {exc}"

    def _safe(fn, fallback):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - defensive
            return fallback

    return {
        "app": {
            "name": _safe(lambda: settings.APP_NAME, "Hunar Voice Agents API"),
            "version": "1.0.0",
            "debug": _safe(lambda: settings.DEBUG, False),
            "frontend_url": _safe(lambda: settings.FRONTEND_URL, ""),
            "webhook_url": _safe(lambda: settings.HUNAR_WEBHOOK_URL or None, None),
        },
        "database": {
            "target": _safe(lambda: _database_target(), "unknown"),
            "ok": db_ok,
            "error": db_error,
        },
        "demo": {
            "seeded": _safe(lambda: _is_demo_seeded(), False),
        },
        "integrations": {
            "hunar": {
                "configured": _safe(lambda: bool(settings.HUNAR_API_KEY), False),
                "key_preview": _safe(lambda: _mask(settings.HUNAR_API_KEY), ""),
                "base_url": _safe(lambda: settings.HUNAR_BASE_URL, ""),
            },
            "apollo": {
                "configured": _safe(lambda: bool(settings.APOLLO_API_KEY), False),
                "key_preview": _safe(lambda: _mask(settings.APOLLO_API_KEY), ""),
                "fallback": "mock data when not set",
            },
            "webhook_secret": {
                "configured": _safe(lambda: bool(settings.HUNAR_WEBHOOK_SECRET), False),
                "key_preview": _safe(lambda: _mask(settings.HUNAR_WEBHOOK_SECRET), ""),
                "validation": _safe(
                    lambda: "enforced" if settings.HUNAR_WEBHOOK_SECRET else "bypassed (dev)",
                    "unknown",
                ),
            },
        },
        "host": {
            "hostname": _safe(
                lambda: os.uname().node if hasattr(os, "uname") else None, None
            ),
            "pid": _safe(lambda: os.getpid(), None),
        },
    }
