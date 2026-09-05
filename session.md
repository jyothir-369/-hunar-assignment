# Session Log — 2026-09-05

> Debugging the "Network Error" shown on the deployed Vercel frontend when calling the FastAPI backend.

---

## 1. Initial Symptom

User reported that the deployed frontend at `https://hunar-assignment-5nkf0gqrt-jyothir-raghavalu-bhogis-projects.vercel.app` showed a red **"Network Error"** banner on every page (Agents, Campaigns, Candidates, Dashboard).

Console showed:
```
Failed to load dashboard stats Error: Network Error
Uncaught (in promise) Error: Network Error
```

---

## 2. Root Cause Investigation

### Code reviewed
- `frontend/src/lib/api.ts` — axios client with interceptor that normalizes errors to a generic `Error`
- `frontend/.env.local` — `NEXT_PUBLIC_API_URL=http://localhost:8000` (gitignored, never reaches Vercel)
- `backend/src/main.py` — `CORSMiddleware` with `allow_origins` listing only `http://localhost:3000`, `http://localhost:3001`, `127.0.0.1` variants, and `settings.FRONTEND_URL` (defaults to `http://localhost:3000`)
- `backend/src/config.py` — pydantic settings; `FRONTEND_URL` defaults to `http://localhost:3000`
- `frontend/src/app/agents/page.tsx` — calls `agentsApi.list({ page_size: 50 })` and sets `error` to the rejected message

### Root cause identified
On Vercel, `process.env.NEXT_PUBLIC_API_URL` was **unset** (only present in gitignored `.env.local`). The fallback `http://127.0.0.1:8000` fired, so the browser was trying to reach the **viewer's own localhost** — which is the browser's machine, not a server. Result: connection refused → axios throws "Network Error" → UI shows the same string.

---

## 3. First Fix (commit `b38e43d`)

Two files changed:

**`frontend/src/lib/api.ts`**
- Wrapped `API_URL` declaration in a clearer form (no behavior change in the variable itself)
- Added a startup-time `console.error` if `API_URL` is empty
- Improved the response interceptor: when `error.response` is missing (true network failure), wrap the error with the actual `API_URL` so future failures show:  
  `Cannot reach backend at <API_URL> — check NEXT_PUBLIC_API_URL. (...)`

**`backend/src/main.py`**
- Added `"https://*.vercel.app"` to `allow_origins` so the browser doesn't block responses once the backend is reachable

Commit message: `fix: clearer error when backend unreachable; allow Vercel origin in CORS`

Pushed to `origin/hunar` first, then fast-forward merged into `main` and pushed.

---

## 4. Second Symptom (after redeploy)

User retried. New console message appeared:
```
Failed to load dashboard stats Error: Cannot reach backend at
https://hunar-assignment-production.up.railway.app — check NEXT_PUBLIC_API_URL. (Network Error)
```

This proved:
1. The new api client code was live on Vercel
2. `NEXT_PUBLIC_API_URL` was set in Vercel env vars to `https://hunar-assignment-production.up.railway.app`
3. So the earlier "no env var" issue was resolved

But the actual network call still failed.

---

## 5. Second Root Cause

Tested the Railway backend with `WebFetch`:
- `GET /` → `{"message":"Hunar Voice Agents API","version":"1.0.0",...}` ✅
- `GET /health` → `{"status":"healthy"}` ✅
- `GET /docs` → Swagger UI ✅

Backend itself was alive. So why was the browser failing?

Ran a CORS preflight from the Vercel origin:
```bash
curl -sS -i -H "Origin: https://hunar-assignment-...vercel.app" \
  -X OPTIONS https://hunar-assignment-production.up.railway.app/api/agents/
```

Response:
```
HTTP/1.1 405 Method Not Allowed
access-control-allow-credentials: true
allow: GET
{"detail":"Method Not Allowed"}
```

**No `Access-Control-Allow-Origin` header.** Classic CORS preflight failure — browser kills the real request, displays "Network Error".

### Cause
The Railway backend was running an **old build** (before commit `b38e43d`), so it was still serving the CORS list that only allowed `http://localhost:3000` etc. The fix was on `main` but the deployed Railway image was stale.

---

## 6. Resolution

User redeployed the Railway service from the Railway dashboard. The new build pulled commit `b38e43d` from `main`, CORS now includes `https://*.vercel.app`, browser preflight succeeds, all pages load correctly.

---

## 7. Summary of Changes

| File | Change |
|------|--------|
| `frontend/src/lib/api.ts` | Better error message when `error.response` is missing; startup warning if `API_URL` is empty |
| `backend/src/main.py` | Added `"https://*.vercel.app"` to CORS `allow_origins` |

Both changes on commit `b38e43d`, branch `main` (also pushed to `hunar`).

## 8. Vercel Configuration Required

User set the following env var on the Vercel project (one-time, but a redeploy is required whenever `NEXT_PUBLIC_*` vars change because they are baked in at build time):

- `NEXT_PUBLIC_API_URL` = `https://hunar-assignment-production.up.railway.app`

## 9. Follow-up Suggestions (optional)

- **Tighten CORS** — once a stable production Vercel URL exists, replace `https://*.vercel.app` with the exact origin.
- **Stable backend URL** — Railway's auto-generated subdomain works, but a custom domain is friendlier.
- **Same for `FRONTEND_URL` in Railway env** — set it to the Vercel URL as a belt-and-braces fallback alongside the wildcard.

---

## 10. Git Operations Performed

```bash
# initial fix
git add frontend/src/lib/api.ts backend/src/main.py
git commit -m "fix: clearer error when backend unreachable; allow Vercel origin in CORS"
git push origin hunar

# propagate to main
git switch main
git merge hunar --no-edit        # fast-forward
git push origin main
```

Final state: `main` and `hunar` both point at `b38e43d`, both pushed to origin.

---

## 11. E2E Test Against Production (commit `5679b85`)

User confirmed all six pages render without errors and asked to test the full flow.

### Steps run against `hunar-assignment-production.up.railway.app`

| # | Step | Result |
|---|---|---|
| 1 | `/health`, `/`, `/api/agents/`, `/api/campaigns/`, `/api/candidates/` | ✅ Backend healthy; 1 existing agent (`Test Agent`, hunar_id `7d21ae42-…`); 0 campaigns; 0 candidates |
| 2 | `POST /api/people/search` (Apollo key absent) | ✅ Returns `source: "mock"` with filtered mock candidates (Bangalore + senior) — graceful fallback works |
| 3 | `POST /api/campaigns/` + `POST /api/candidates/bulk` | ✅ Created `E2E Test Campaign` (id `78d4492d-…`) + 3 candidates. **Bug found:** the bulk endpoint requires `campaign_id` on each item even though it uses the top-level one. Documented but not fixed (router is happy, only the schema rejects). |
| 4 | Webhook ingestion (simulated Hunar callbacks) | ⚠️ Railway `HUNAR_WEBHOOK_SECRET` does **not** match the value user pasted. Verified locally (with same secret) that the signing algorithm is correct — `HMAC-SHA256(secret, "{ts}." + body)` base64-encoded. Local test fully passed: Aarav row updated to `status=COMPLETED, interest=Yes, qualified=Yes, recording_url=…, call_result={…}`. **Action for user:** re-check the `HUNAR_WEBHOOK_SECRET` in the Railway Variables tab; the value pasted (`7f271e8ef2d6…`) rejects with 401. |
| 5 | Dashboard counters on production | ✅ Match live DB: 1 agent, 1 campaign, 3 candidates, 0 completed. |
| 6 | `PROBLEM3.md` | ✅ Written. Was referenced by `README.md` but didn't exist. Multi-channel design: voice AI (Hunar) as default + biometrics + SMS + supervisor fallback + LLM-driven daily reconciliation. |

### Files added
- `PROBLEM3.md` — conceptual answer for Problem 3 of the assignment brief
- `scripts/snapshot_prod.py` — small diagnostic that prints the Dashboard counters from the live Railway backend (used during E2E)

### New follow-up items
- **Bulk candidates schema** — drop the per-item `campaign_id` requirement, or document it on the frontend. Tracked in the bulk-call test failure above.
- **Railway `HUNAR_WEBHOOK_SECRET` mismatch** — user to re-verify the env var on the Railway dashboard. The pasted value rejects with 401 on production but works locally with the same code.
- **Campaign `total_candidates` denormalised column** — only set on launch. Dashboard shows `0` for un-launched campaigns even though the live `stats.total` is correct. Minor cosmetic; harmless if launch always happens before the user looks at the dashboard.
