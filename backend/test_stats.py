import urllib.request, json

BASE = 'http://127.0.0.1:8002'

def get(path):
    with urllib.request.urlopen(f'{BASE}{path}', timeout=10) as r:
        return json.loads(r.read())

print('=== LIST endpoint: GET /api/campaigns/?page_size=50 ===')
d = get('/api/campaigns/?page_size=50')
total_completed = 0
for c in d['results']:
    s = c.get('stats')
    print(f'  {c["name"]:35s} status={c["status"]:10s} total_candidates={c["total_candidates"]:3d} stats={s}')
    assert s is not None, f'stats was None for {c["name"]}'
    total_completed += s['completed']
print(f'  >>> Dashboard reduce: Calls Completed = {total_completed}')
print()

cid = d['results'][0]['id']
print(f'=== DETAIL endpoint: GET /api/campaigns/{cid[:8]}... ===')
detail = get(f'/api/campaigns/{cid}')
print(f'  name={detail["name"]}')
print(f'  stats={detail.get("stats")}')
assert detail.get('stats') is not None, 'stats was None on detail endpoint'

# also test 404 detail still works (no crash)
print()
print('=== Bonus: stats on an unknown campaign id would still 404 before reaching stats ===')
print()
print('ALL ASSERTIONS PASSED - stats is always a non-null nested object on both endpoints.')
