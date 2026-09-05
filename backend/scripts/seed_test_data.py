"""Seed the local DB with a Hunar agent, a campaign, and 3 test candidates.

This script drives the running FastAPI server over HTTP. It expects:
    - uvicorn src.main:app --reload --port 8000   (already running)
    - HUNAR_API_KEY set in backend/.env

What it does, in order:
    1. POST /api/agents/            -> create a real Hunar agent
    2. POST /api/campaigns/         -> create a local campaign
    3. POST /api/candidates/bulk    -> add 3 candidates
    4. POST /api/campaigns/{id}/launch -> trigger Hunar bulk calls
    5. Writes ./seed_output.json with the resulting ids

Run from the backend/ directory:
    python scripts/seed_test_data.py
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any

# Force UTF-8 on stdout so the script works on Windows consoles (cp1252 default).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:  # pragma: no cover
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Allow running this script directly (`python scripts/seed_test_data.py`)
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx  # noqa: E402

from src.config import settings  # noqa: E402

API_BASE = "http://127.0.0.1:8000"
OUTPUT_PATH = BACKEND_ROOT / "seed_output.json"

AGENT_PAYLOAD: dict[str, Any] = {
    "name": "Hunar Recruiter Agent",
    "language": "ENGLISH",
    "voice_persona": "NEHA",
    "persona_name": "Priya",
    "agent_prompt": (
        "You are a professional HR recruiter calling candidates named {callee_name}. "
        "Introduce yourself and the job opportunity clearly. "
        "Ask screening questions: interest level, availability, "
        "salary expectations, and notice period. "
        "Be friendly, concise, and professional."
    ),
    "introduction": (
        "Hi {callee_name}! This is {persona_name} calling from Hunar regarding "
        "the {job_title} role at {company}. Do you have a few minutes to chat?"
    ),
    "objective": (
        "Screen candidates for the {job_title} role at {company}, "
        "collecting interest level, availability, salary expectations, and notice period."
    ),
    "result_prompt": (
        "From this conversation, extract: whether the candidate is interested "
        "(yes/no/maybe), their qualification status, expected salary, "
        "notice period, and any relevant notes."
    ),
    "result_schema": {
        "interested": "Yes | No | Maybe",
        "qualified": "Yes | No | Needs Review",
        "salary_expectation": "number (in Lakhs per annum)",
        "notice_period_weeks": "number",
        "notes": "string",
    },
}

TEST_CANDIDATES: list[dict[str, Any]] = [
    {
        "callee_name": "Asha Reddy",
        "mobile_number": "+919876543210",
        "email": "asha.reddy@example.com",
        "custom_data": {"company": "Acme", "job_title": "Software Engineer"},
    },
    {
        "callee_name": "Rohit Kumar",
        "mobile_number": "+919876543211",
        "email": "rohit.kumar@example.com",
        "custom_data": {"company": "Globex", "job_title": "Data Analyst"},
    },
    {
        "callee_name": "Sneha Iyer",
        "mobile_number": "+919876543212",
        "email": "sneha.iyer@example.com",
        "custom_data": {"company": "Initech", "job_title": "Product Manager"},
    },
]


def _request(method: str, path: str, **kwargs: Any) -> tuple[int, Any]:
    """Make an HTTP request, returning (status_code, parsed_body)."""
    url = f"{API_BASE}{path}"
    with httpx.Client(timeout=60.0) as client:
        response = client.request(method, url, **kwargs)
    try:
        body: Any = response.json()
    except Exception:
        body = response.text
    return response.status_code, body


def _abort(step: str, status: int, body: Any) -> None:
    """Print full details and exit."""
    print(f"\n❌ {step} failed (HTTP {status})")
    print("Full response body:")
    print(json.dumps(body, indent=2, default=str) if not isinstance(body, str) else body)
    raise SystemExit(1)


def main() -> None:
    if not settings.HUNAR_API_KEY:
        print("❌ HUNAR_API_KEY is not set in .env — cannot seed Hunar agent.")
        raise SystemExit(1)

    # 1. Create or reuse agent
    print("→ GET /api/agents/  (looking for existing 'Hunar Recruiter Agent')")
    status, body = _request(
        "GET", "/api/agents/", params={"page_size": 50}
    )
    if status >= 400:
        _abort("List agents", status, body)
    existing = next(
        (a for a in body.get("results", []) if a.get("name") == AGENT_PAYLOAD["name"]),
        None,
    )

    if existing:
        agent = existing
        print(f"   ↻ Reusing local agent: {agent['id']} (Hunar: {agent['hunar_agent_id']})")
    else:
        print("→ POST /api/agents/")
        status, body = _request("POST", "/api/agents/", json=AGENT_PAYLOAD)
        if status >= 400:
            _abort("Create agent", status, body)
        agent = body
        print(f"   ✓ Local agent id:    {agent['id']}")
        print(f"   ✓ Hunar agent id:    {agent['hunar_agent_id']}")

    # 2. Create or reuse campaign
    print("→ GET /api/campaigns/  (looking for existing 'Q4 Engineering Hiring')")
    status, body = _request(
        "GET", "/api/campaigns/", params={"page_size": 50}
    )
    if status >= 400:
        _abort("List campaigns", status, body)
    existing_camp = next(
        (c for c in body.get("results", []) if c.get("name") == "Q4 Engineering Hiring"),
        None,
    )

    if existing_camp and existing_camp.get("status") != "LAUNCHED":
        campaign = existing_camp
        print(f"   ↻ Reusing local campaign: {campaign['id']} (status: {campaign['status']})")
    elif existing_camp and existing_camp.get("status") == "LAUNCHED":
        # Already launched — clear candidates so we can re-seed cleanly
        print(f"   ↻ Re-launching campaign {existing_camp['id']} (was LAUNCHED)")
        campaign = existing_camp
    else:
        print("→ POST /api/campaigns/")
        campaign_payload = {
            "name": "Q4 Engineering Hiring",
            "agent_id": agent["id"],
            "job_title": "Software Engineer",
            "job_description": "Backend / full-stack role in Bangalore.",
            "guardrails": {},
            "retry_config": {"max_retries": 2, "retry_interval_minutes": 60},
            "timezone": "Asia/Kolkata",
        }
        status, body = _request("POST", "/api/campaigns/", json=campaign_payload)
        if status >= 400:
            _abort("Create campaign", status, body)
        campaign = body
        print(f"   ✓ Local campaign id: {campaign['id']}")

    # 3. Bulk add candidates
    print("→ POST /api/candidates/bulk")
    bulk_payload = {
        "campaign_id": campaign["id"],
        "candidates": [
            {
                "campaign_id": campaign["id"],
                "callee_name": c["callee_name"],
                "mobile_number": c["mobile_number"],
                "email": c["email"],
                "custom_data": c["custom_data"],
            }
            for c in TEST_CANDIDATES
        ],
    }
    status, body = _request("POST", "/api/candidates/bulk", json=bulk_payload)
    if status >= 400:
        _abort("Bulk create candidates", status, body)
    created_ids: list[str] = list(body.get("candidate_ids") or [])
    print(f"   ✓ Created {len(created_ids)} candidates")
    for c in TEST_CANDIDATES:
        print(f"      - {c['callee_name']} ({c['mobile_number']})")

    # 4. Launch campaign
    print(f"→ POST /api/campaigns/{campaign['id']}/launch")
    status, body = _request(
        "POST",
        f"/api/campaigns/{campaign['id']}/launch",
        json={"timezone": "Asia/Kolkata"},
    )
    if status >= 400:
        _abort("Launch campaign", status, body)
    launched = body
    print(f"   ✓ Campaign status:   {launched.get('status')}")
    print(f"   ✓ Total candidates:  {launched.get('total_candidates')}")

    # 5. Fetch each candidate to retrieve hunar_call_id assigned by /launch
    print("→ GET /api/candidates/  (fetching hunar_call_id per candidate)")
    status, body = _request(
        "GET",
        "/api/candidates/",
        params={"campaign_id": campaign["id"], "page_size": 50},
    )
    if status >= 400:
        _abort("List candidates", status, body)
    candidates = body.get("results") or []
    candidate_ids = [c["id"] for c in candidates]
    hunar_call_ids = [c.get("hunar_call_id") for c in candidates]

    # 6. Write seed_output.json
    output = {
        "agent_id": agent["id"],
        "hunar_agent_id": agent["hunar_agent_id"],
        "campaign_id": campaign["id"],
        "candidate_ids": candidate_ids,
        "hunar_call_ids": hunar_call_ids,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\n✅ Wrote {OUTPUT_PATH.relative_to(BACKEND_ROOT)}")
    print(json.dumps(output, indent=2))

    if any(not cid for cid in hunar_call_ids):
        print(
            "\n⚠️  Some candidates did not receive a hunar_call_id. "
            "Inspect the API response above — the bulk endpoint may not have "
            "returned a per-row id in the expected shape."
        )


if __name__ == "__main__":
    main()
