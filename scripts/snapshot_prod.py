"""Snapshot the production backend for Dashboard verification."""
import json
import urllib.request

BASE = "https://hunar-assignment-production.up.railway.app"


def get(path):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=15) as r:
        return json.loads(r.read())


agents = get("/api/agents/")
campaigns = get("/api/campaigns/")
candidates = get("/api/candidates/")

print("=== AGENTS ===")
print(f"count={agents['count']}")
for a in agents["results"]:
    print(f"  - {a['name']} status={a['status']} hunar={a['hunar_agent_id']}")

print("\n=== CAMPAIGNS ===")
print(f"count={campaigns['count']}")
for c in campaigns["results"]:
    print(
        f"  - {c['name']} status={c['status']} "
        f"agent={c['agent_id'][:8]}... total_candidates={c['total_candidates']}"
    )

print("\n=== CANDIDATES ===")
print(f"count={candidates['count']}")
for c in candidates["results"]:
    print(
        f"  - {c['callee_name']:<15} status={c['status']:<12} "
        f"interest={c.get('interest_level')} qualified={c.get('qualification_status')}"
    )

# What the Dashboard would render
print("\n=== DASHBOARD COUNTERS ===")
print(f"Total Agents:      {agents['count']}")
print(f"Total Campaigns:   {campaigns['count']}")
print(f"Total Candidates:  {candidates['count']}")
completed = sum(1 for c in candidates["results"] if c["status"] == "COMPLETED")
print(f"Calls Completed:   {completed}")
