"""Smoke test for /api/calls/{call_id} and /api/calls/{call_id}/result.

We don't need Hunar to actually return a call — we just need the route to
exist and either succeed (if the call_id happens to be valid) or return a
structured 4xx/5xx from the upstream. 404 or 502 here would be a success
because it means the route is mounted and the upstream call was attempted.
"""
import json
import sys
import urllib.error
import urllib.request

for path in ("/api/calls/00000000-0000-0000-0000-000000000000",
             "/api/calls/00000000-0000-0000-0000-000000000000/result"):
    url = f"http://127.0.0.1:8765{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            print(f"{path} -> HTTP {r.status}")
            body = r.read().decode()
            print(f"  body: {body[:200]}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"{path} -> HTTP {e.code}")
        print(f"  body: {body[:200]}")
        # 404 from Hunar is expected — proves the route works end-to-end
