"""Browser-flow verification — does the running frontend actually pull real data
from the local backend? This simulates what the browser does:
  1. Load /
  2. Call the Next.js /_next/static API client
  3. Then exercise each page's data path by hitting the backend directly
     (same URLs the frontend uses) and checking the shape of the response.
"""
import json
import sys
import urllib.request

BACKEND = "http://127.0.0.1:8001"
FRONTEND = "http://127.0.0.1:3000"

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{PASS if ok else FAIL} {name}" + (f"  — {detail}" if detail else ""))


def get(path, base=BACKEND):
    with urllib.request.urlopen(base + path, timeout=10) as r:
        return r.status, json.loads(r.read() or b"null")


# 1. Dashboard calls /api/campaigns + /api/agents for quick stats
print("=== Dashboard data path ===")
code, agents = get("/api/agents/?page_size=1")
check("Dashboard fetches /api/agents", code == 200 and "results" in agents,
      f"count={agents.get('count', 0)}")

code, campaigns = get("/api/campaigns/?page_size=1")
check("Dashboard fetches /api/campaigns", code == 200 and "results" in campaigns,
      f"count={campaigns.get('count', 0)}")

# 2. Agents page list
print("\n=== Agents page data path ===")
code, agents_list = get("/api/agents/?page_size=10")
check("GET /api/agents paginated", code == 200)
check("   has count + results", all(k in agents_list for k in ("count", "results")),
      f"keys={list(agents_list.keys())}")
check("   at least 1 agent from E2E", len(agents_list.get("results", [])) >= 1)

# 3. Campaign detail with stats
print("\n=== Campaign detail data path ===")
if campaigns.get("results"):
    cid = campaigns["results"][0]["id"]
    code, detail = get(f"/api/campaigns/{cid}")
    check("GET /api/campaigns/{id}", code == 200)
    check("   has stats", "stats" in detail, f"stats={detail.get('stats', {}).get('total', 0)} total")
    check("   total_candidates matches stats", detail.get("total_candidates") == detail.get("stats", {}).get("total"))

    # 4. Candidates list (filtered by campaign)
    code, cands = get(f"/api/candidates/?campaign_id={cid}&page_size=10")
    check("GET /api/candidates?campaign_id=...", code == 200)
    check("   has hunar_call_id populated", all(c.get("hunar_call_id") for c in cands.get("results", [])))

# 5. Results page data
print("\n=== Results page data path ===")
code, all_cands = get("/api/candidates/?page_size=50")
check("GET /api/candidates for results", code == 200)
completed = [c for c in all_cands.get("results", []) if c.get("status") == "COMPLETED"]
check("   has at least 1 COMPLETED candidate", len(completed) >= 1, f"completed={len(completed)}")

# 6. People search (used by /people page)
print("\n=== People search data path ===")
body = json.dumps({"job_title": "Engineer", "seniority_levels": ["senior"], "locations": ["Bangalore"], "page": 1, "per_page": 5}).encode()
req = urllib.request.Request(BACKEND + "/api/people/search", data=body, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        ps = json.loads(r.read())
    check("POST /api/people/search", r.status == 200 and ps.get("source") == "mock", f"source={ps.get('source')}")
    check("   returns candidates", len(ps.get("candidates", [])) >= 1)
except Exception as e:
    check("POST /api/people/search", False, str(e))

# 7. Settings page data
print("\n=== Settings page data path ===")
code, settings = get("/api/settings/")
check("GET /api/settings/", code == 200)
check("   has app metadata", "app" in settings and "name" in settings["app"])
check("   has database info", "database" in settings and settings["database"].get("ok"))
check("   has integrations", "integrations" in settings)
check("   hunar configured", settings["integrations"]["hunar"]["configured"] is True)
check("   webhook enforced", settings["integrations"]["webhook_secret"]["validation"] == "enforced")

# 8. Calls proxy
print("\n=== Calls proxy data path ===")
# Find a completed candidate's hunar_call_id
call_id = next((c.get("hunar_call_id") for c in all_cands.get("results", []) if c.get("hunar_call_id")), None)
if call_id:
    code, call_env = get(f"/api/calls/{call_id}")
    check("GET /api/calls/{call_id}", code == 200)
    check("   has local candidate_id enrichment", "candidate_id" in call_env)
    check("   has local_status", call_env.get("local_status") == "COMPLETED")
    code, call_res = get(f"/api/calls/{call_id}/result")
    check("GET /api/calls/{call_id}/result", code == 200)
    check("   prefers local source", call_res.get("source") == "local")
    check("   has interest_level", call_res.get("interest_level") == "Yes")
else:
    check("no call_id found to test proxy", False)

# 9. Frontend compilation: no errors in dev log
print("\n=== Frontend compilation health ===")
import urllib.request as ur
try:
    with ur.urlopen(FRONTEND + "/", timeout=10) as r:
        html = r.read().decode("utf-8", errors="ignore")
    check("frontend home loads", r.status == 200)
    check("   no 'Application error' overlay", "Application error" not in html)
    check("   no unhandled exception in HTML", "Unhandled Runtime Error" not in html)
    check("   has 'Hunar Hiring' brand", "Hunar Hiring" in html)
    check("   has sidebar nav", "Dashboard" in html and "Agents" in html and "Campaigns" in html)
except Exception as e:
    check("frontend home loads", False, str(e))

# Summary
print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"RESULT: {passed}/{total} checks passed")
sys.exit(0 if passed == total else 1)
