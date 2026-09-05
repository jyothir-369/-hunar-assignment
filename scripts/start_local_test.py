"""Boot the backend for local E2E testing.

- Uses a separate SQLite DB so we don't touch the user's real data
- Forces a known HUNAR_WEBHOOK_SECRET so we can sign payloads ourselves
- Keeps the real HUNAR_API_KEY (so we hit the real Hunar API)
- Serves on 127.0.0.1:8001 to avoid clashing with prod 8000
"""
import os
import secrets
import sys
from pathlib import Path

# Override env BEFORE any src.* import.
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DB_PATH = ROOT / "scripts" / ".test_app.db"
if DB_PATH.exists():
    DB_PATH.unlink()  # fresh DB each run
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["HUNAR_WEBHOOK_SECRET"] = "test_secret_" + secrets.token_hex(16)
os.environ["DEBUG"] = "true"
# HUNAR_API_KEY, APOLLO_API_KEY, etc. come from backend/.env (read by pydantic-settings
# because cwd at startup is backend/ — see os.chdir below)

# Persist the secret so the E2E test script can sign with the same value.
(Path(__file__).resolve().parent / ".test_webhook_secret").write_text(
    os.environ["HUNAR_WEBHOOK_SECRET"]
)
(Path(__file__).resolve().parent / ".test_db_path").write_text(str(DB_PATH))

# CRITICAL: chdir to backend/ so pydantic-settings finds backend/.env
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    from src.config import settings  # noqa: E402

    print("=" * 60)
    print("Local test backend starting")
    print(f"  cwd:        {os.getcwd()}")
    print(f"  DB:         {DB_PATH}")
    print(f"  Webhook:    enforced ({os.environ['HUNAR_WEBHOOK_SECRET'][:24]}…)")
    print(f"  Hunar key:  {'set (' + str(len(settings.HUNAR_API_KEY)) + ' chars)' if settings.HUNAR_API_KEY else 'NOT SET'}")
    print(f"  Apollo key: {'set' if settings.APOLLO_API_KEY else 'NOT SET (will use mock)'}")
    print("=" * 60)

    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=8001,
        log_level="warning",
        reload=False,
    )
