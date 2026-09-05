"""Smoke test the new /api/settings endpoint via local backend on 8765."""
import json
import sys
import urllib.request

try:
    with urllib.request.urlopen("http://127.0.0.1:8765/api/settings/", timeout=10) as r:
        data = json.loads(r.read().decode())
except Exception as exc:
    print("FAILED to reach /api/settings/:", exc)
    sys.exit(1)

print("OK — got /api/settings/ response")
print(json.dumps(data, indent=2)[:1200])
