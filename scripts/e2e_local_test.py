"""Local E2E test for the Hunar hiring app.

Walks the full recruiter flow against a local backend on :8001 that has the
real HUNAR_API_KEY loaded, but uses a fresh SQLite database and a generated
webhook secret so we can sign payloads ourselves.

Steps:
  1.  /api/settings  — confirm env is right
  2.  POST /api/agents/        — create a real voice agent on Hunar
  3.  POST /api/campaigns/     — create a campaign
  4.  POST /api/candidates/    — add one candidate
  5.  POST /api/candidates/bulk — add two more
  6.  GET  /api/campaigns/{id} — verify stats (3 PENDING)
  7.  POST /api/campaigns/{id}/launch — triggers Hunar /calls/bulk/
  8.  GET  /api/campaigns/{id} — verify 3 candidates now have hunar_call_id + status INITIATED
  9.  POST /webhooks/hunar (×4 events) — with valid HMAC, verify candidate fields update
  10. GET  /api/calls/{call_id} — verify proxy returns the call + local candidate id
  11. GET  /api/calls/{call_id}/result — verify returns the local cached result
  12. POST /api/people/search — verify mock fallback (Apollo key not set)
  13. /api/agents/?page_size=1 — sanity (this was the live 500; check local)

Each step prints a single PASS/FAIL line. Non-zero exit if any step fails.
"""
import base64
import hashlib
import hmac
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8001"
SCRIPTS = Path(__file__).resolve().parent
WEBHOOK_SECRET = SCRIPTS.joinpath(".test_webhook_secret").read_text().strip()


def http(method, path, body=None, *, sign_as_webhook=False):
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        if sign_as_webhook:
            ts = str(int(time.time()))
            msg = ts.encode("utf-8") + b"." + data
            sig = base64.b64encode(
                hmac.new(WEBHOOK_SECRET.encode("utf-8"), msg, hashlib.sha256).digest()
            ).decode("ascii")
            headers["X-Hunar-Signature"] = sig
            headers["X-Hunar-Timestamp"] = ts
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
results = []


def step(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{PASS if ok else FAIL} {name}" + (f"  — {detail}" if detail else ""))


# 1. /api/settings
print("\n=== Step 1: /api/settings ===")
code, d = http("GET", "/api/settings/")
step("1. /api/settings reachable", code == 200)
step(
    "   hunar key loaded",
    d["integrations"]["hunar"]["configured"] is True,
    f"key_preview={d['integrations']['hunar']['key_preview'][:30]}",
)
step(
    "   webhook secret enforced",
    d["integrations"]["webhook_secret"]["validation"] == "enforced",
    d["integrations"]["webhook_secret"]["validation"],
)
step("   fresh DB", d["database"]["ok"] and "test_app" in d["database"]["target"])

# 2. Create agent on real Hunar
print("\n=== Step 2: POST /api/agents/ (real Hunar) ===")
agent_body = {
    "name": "LocalE2E Test Recruiter",
    "voice_persona": "NEHA",
    "persona_name": "Priya",
    "language": "ENGLISH",
    "agent_prompt": "You are a recruiter screening candidates for a backend role.",
    "introduction": "Hi {callee_name}, this is {persona_name} calling from Hunar.",
    "objective": "Screen candidates briefly.",
    "result_prompt": "Extract interest and qualification.",
    "result_schema": {
        "interested": "Yes | No | Maybe",
        "qualified": "Yes | No | Needs Review",
    },
}
code, agent = http("POST", "/api/agents/", agent_body)
step("2. POST /api/agents/ creates on Hunar + DB", code == 201, f"status={code}")
agent_id = agent.get("id") if isinstance(agent, dict) else None
hunar_agent_id = agent.get("hunar_agent_id") if isinstance(agent, dict) else None
step("   returns local id", bool(agent_id))
step("   returns hunar_agent_id", bool(hunar_agent_id), str(hunar_agent_id))

# 3. Create campaign
print("\n=== Step 3: POST /api/campaigns/ ===")
code, campaign = http(
    "POST",
    "/api/campaigns/",
    {
        "name": "LocalE2E Campaign",
        "agent_id": agent_id,
        "job_title": "Backend Engineer",
        "job_description": "Build APIs.",
        "timezone": "Asia/Kolkata",
        "guardrails": {
            "allowed_days": ["MON", "TUE", "WED", "THU", "FRI"],
            "earliest_call_time": "09:00",
            "last_call_time": "18:00",
        },
        "retry_config": {"max_retries": 2, "retry_interval_minutes": 360},
    },
)
step("3. POST /api/campaigns/", code == 201, f"status={code}")
campaign_id = campaign.get("id") if isinstance(campaign, dict) else None
step("   returns campaign id", bool(campaign_id))

# 4. Single candidate
print("\n=== Step 4: POST /api/candidates/ ===")
code, c1 = http(
    "POST",
    "/api/candidates/",
    {
        "campaign_id": campaign_id,
        "callee_name": "Anita Test",
        "mobile_number": "+919999000001",
        "email": "anita@example.com",
        "custom_data": {"title": "Backend Engineer"},
    },
)
step("4. POST /api/candidates/ single", code == 201, f"status={code}")
c1_id = c1.get("id") if isinstance(c1, dict) else None

# 5. Bulk candidates
print("\n=== Step 5: POST /api/candidates/bulk ===")
code, bulk = http(
    "POST",
    "/api/candidates/bulk",
    {
        "campaign_id": campaign_id,
        "candidates": [
            {
                "callee_name": "Bharat Test",
                "mobile_number": "+919999000002",
                "custom_data": {"title": "Backend Engineer"},
            },
            {
                "callee_name": "Chitra Test",
                "mobile_number": "+919999000003",
                "custom_data": {"title": "Backend Engineer"},
            },
        ],
    },
)
step("5. POST /api/candidates/bulk", code == 201, f"status={code}")
step(
    "   created 2 candidates",
    isinstance(bulk, dict) and bulk.get("created") == 2,
    f"created={bulk.get('created') if isinstance(bulk, dict) else bulk}",
)

# 6. Campaign stats
print("\n=== Step 6: GET /api/campaigns/{id} stats ===")
code, cstats = http("GET", f"/api/campaigns/{campaign_id}")
step("6. GET /api/campaigns/{id}", code == 200)
step(
    "   3 PENDING candidates",
    isinstance(cstats, dict)
    and cstats.get("stats", {}).get("total") == 3
    and cstats.get("stats", {}).get("pending") == 3,
    f"total={cstats.get('stats', {}).get('total')} pending={cstats.get('stats', {}).get('pending')}",
)

# 7. Launch campaign
print("\n=== Step 7: POST /api/campaigns/{id}/launch (real Hunar) ===")
code, launched = http(
    "POST",
    f"/api/campaigns/{campaign_id}/launch",
    {},
)
step(
    "7. POST /api/campaigns/{id}/launch returns 200",
    code == 200,
    f"status={code} detail={launched.get('detail') if isinstance(launched, dict) else ''}",
)

# 8. After launch: candidates should have hunar_call_id + INITIATED
print("\n=== Step 8: GET /api/candidates/?campaign_id=... ===")
code, clist = http(
    "GET",
    f"/api/candidates/?campaign_id={campaign_id}&page_size=10",
)
step("8. GET /api/candidates/", code == 200)
candidates = clist.get("results", []) if isinstance(clist, dict) else []
hunar_ids = [c.get("hunar_call_id") for c in candidates]
step(
    "   all 3 candidates have hunar_call_id",
    len(candidates) == 3 and all(hunar_ids),
    f"hunar_call_ids={hunar_ids}",
)
step(
    "   all 3 candidates INITIATED",
    all(c.get("status") == "INITIATED" for c in candidates),
    f"statuses={[c.get('status') for c in candidates]}",
)

# 9. Simulate the 4 webhook events
print("\n=== Step 9: POST /webhooks/hunar (4 events) ===")
target_call_id = next(c.get("hunar_call_id") for c in candidates if c.get("hunar_call_id"))
target_candidate_id = next(
    c.get("id") for c in candidates if c.get("hunar_call_id") == target_call_id
)

# 9a. call_status_updated
code, _ = http(
    "POST",
    "/webhooks/hunar",
    {
        "event_type": "call_status_updated",
        "call_id": target_call_id,
        "request_id": f"campaign-{campaign_id}",
        "status": "IN_PROGRESS",
    },
    sign_as_webhook=True,
)
step("9a. call_status_updated accepted", code == 200, f"status={code}")

# 9b. call_recording_done
code, _ = http(
    "POST",
    "/webhooks/hunar",
    {
        "event_type": "call_recording_done",
        "call_id": target_call_id,
        "request_id": f"campaign-{campaign_id}",
        "recording_url": "https://recordings.example/local-e2e.mp3",
    },
    sign_as_webhook=True,
)
step("9b. call_recording_done accepted", code == 200, f"status={code}")

# 9c. call_result_done
code, _ = http(
    "POST",
    "/webhooks/hunar",
    {
        "event_type": "call_result_done",
        "call_id": target_call_id,
        "request_id": f"campaign-{campaign_id}",
        "result": {
            "interested": "Yes",
            "qualified": "Yes",
            "salary_expectation": 25,
        },
    },
    sign_as_webhook=True,
)
step("9c. call_result_done accepted", code == 200, f"status={code}")

# 9d. call_summary
code, _ = http(
    "POST",
    "/webhooks/hunar",
    {
        "event_type": "call_summary",
        "call_id": target_call_id,
        "request_id": f"campaign-{campaign_id}",
        "lifecycle_status": "COMPLETED",
        "recording_url": "https://recordings.example/local-e2e.mp3",
        "result": {
            "interested": "Yes",
            "qualified": "Yes",
            "notes": "Strong fit",
        },
    },
    sign_as_webhook=True,
)
step("9d. call_summary accepted", code == 200, f"status={code}")

# 9e. Verify the candidate updated
code, cfinal = http("GET", f"/api/candidates/{target_candidate_id}")
step(
    "   candidate status COMPLETED",
    isinstance(cfinal, dict) and cfinal.get("status") == "COMPLETED",
    f"status={cfinal.get('status') if isinstance(cfinal, dict) else cfinal}",
)
step(
    "   interest_level=Yes",
    isinstance(cfinal, dict) and cfinal.get("interest_level") == "Yes",
    f"interest={cfinal.get('interest_level') if isinstance(cfinal, dict) else cfinal}",
)
step(
    "   qualification_status=Yes",
    isinstance(cfinal, dict) and cfinal.get("qualification_status") == "Yes",
    f"qual={cfinal.get('qualification_status') if isinstance(cfinal, dict) else cfinal}",
)
step(
    "   recording_url set",
    isinstance(cfinal, dict) and bool(cfinal.get("recording_url")),
    f"rec={cfinal.get('recording_url') if isinstance(cfinal, dict) else cfinal}",
)
step(
    "   call_result stored",
    isinstance(cfinal, dict)
    and isinstance(cfinal.get("call_result"), dict)
    and cfinal["call_result"].get("interested") == "Yes",
    f"result={cfinal.get('call_result') if isinstance(cfinal, dict) else cfinal}",
)

# 9f. Test signature rejection (negative case)
code, _ = http(
    "POST",
    "/webhooks/hunar",
    {
        "event_type": "call_status_updated",
        "call_id": target_call_id,
        "status": "FAILED",
    },
    sign_as_webhook=False,  # unsigned → should 401
)
step("9f. unsigned webhook rejected with 401", code == 401, f"status={code}")

# 10. /api/calls/{call_id}
print("\n=== Step 10: GET /api/calls/{call_id} ===")
code, cenv = http("GET", f"/api/calls/{target_call_id}")
step("10. GET /api/calls/{call_id} reachable", code == 200, f"status={code}")
step(
    "   returns candidate_id (enrichment)",
    isinstance(cenv, dict) and cenv.get("candidate_id") == target_candidate_id,
    f"candidate_id={cenv.get('candidate_id') if isinstance(cenv, dict) else cenv}",
)
step(
    "   returns local_status",
    isinstance(cenv, dict) and cenv.get("local_status") == "COMPLETED",
    f"local_status={cenv.get('local_status') if isinstance(cenv, dict) else cenv}",
)

# 11. /api/calls/{call_id}/result
print("\n=== Step 11: GET /api/calls/{call_id}/result ===")
code, cres = http("GET", f"/api/calls/{target_call_id}/result")
step("11. GET /api/calls/{call_id}/result", code == 200, f"status={code}")
step(
    "   source=local (preferred cache)",
    isinstance(cres, dict) and cres.get("source") == "local",
    f"source={cres.get('source') if isinstance(cres, dict) else cres}",
)
step(
    "   interest_level returned",
    isinstance(cres, dict) and cres.get("interest_level") == "Yes",
    f"interest={cres.get('interest_level') if isinstance(cres, dict) else cres}",
)

# 12. /api/people/search (mock fallback)
print("\n=== Step 12: POST /api/people/search (mock fallback) ===")
code, psearch = http(
    "POST",
    "/api/people/search",
    {
        "job_title": "Engineer",
        "seniority_levels": ["senior"],
        "locations": ["Bangalore"],
        "page": 1,
        "per_page": 5,
    },
)
step("12. POST /api/people/search", code == 200, f"status={code}")
step(
    "   source=mock (no Apollo key)",
    isinstance(psearch, dict) and psearch.get("source") == "mock",
    f"source={psearch.get('source') if isinstance(psearch, dict) else psearch}",
)
step(
    "   returns at least 1 candidate",
    isinstance(psearch, dict) and len(psearch.get("candidates", [])) >= 1,
    f"count={len(psearch.get('candidates', [])) if isinstance(psearch, dict) else 0}",
)

# 13. /api/agents/?page_size=1 (the live 500)
print("\n=== Step 13: /api/agents/?page_size=1 (live 500 repro) ===")
code, _ = http("GET", "/api/agents/?page_size=1")
step("13. /api/agents/?page_size=1 returns 200", code == 200, f"status={code}")

# Summary
print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"RESULT: {passed}/{total} checks passed")
if passed < total:
    print("FAILED:")
    for name, ok, detail in results:
        if not ok:
            print(f"  - {name}: {detail}")
    sys.exit(1)
else:
    print("All checks green. Ready to PR.")
    sys.exit(0)
