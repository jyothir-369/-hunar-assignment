# Session Log â€” 2026-09-05

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
- `frontend/src/lib/api.ts` â€” axios client with interceptor that normalizes errors to a generic `Error`
- `frontend/.env.local` â€” `NEXT_PUBLIC_API_URL=http://localhost:8000` (gitignored, never reaches Vercel)
- `backend/src/main.py` â€” `CORSMiddleware` with `allow_origins` listing only `http://localhost:3000`, `http://localhost:3001`, `127.0.0.1` variants, and `settings.FRONTEND_URL` (defaults to `http://localhost:3000`)
- `backend/src/config.py` â€” pydantic settings; `FRONTEND_URL` defaults to `http://localhost:3000`
- `frontend/src/app/agents/page.tsx` â€” calls `agentsApi.list({ page_size: 50 })` and sets `error` to the rejected message

### Root cause identified
On Vercel, `process.env.NEXT_PUBLIC_API_URL` was **unset** (only present in gitignored `.env.local`). The fallback `http://127.0.0.1:8000` fired, so the browser was trying to reach the **viewer's own localhost** â€” which is the browser's machine, not a server. Result: connection refused â†’ axios throws "Network Error" â†’ UI shows the same string.

---

## 3. First Fix (commit `b38e43d`)

Two files changed:

**`frontend/src/lib/api.ts`**
- Wrapped `API_URL` declaration in a clearer form (no behavior change in the variable itself)
- Added a startup-time `console.error` if `API_URL` is empty
- Improved the response interceptor: when `error.response` is missing (true network failure), wrap the error with the actual `API_URL` so future failures show:  
  `Cannot reach backend at <API_URL> â€” check NEXT_PUBLIC_API_URL. (...)`

**`backend/src/main.py`**
- Added `"https://*.vercel.app"` to `allow_origins` so the browser doesn't block responses once the backend is reachable

Commit message: `fix: clearer error when backend unreachable; allow Vercel origin in CORS`

Pushed to `origin/hunar` first, then fast-forward merged into `main` and pushed.

---

## 4. Second Symptom (after redeploy)

User retried. New console message appeared:
```
Failed to load dashboard stats Error: Cannot reach backend at
https://hunar-assignment-production.up.railway.app â€” check NEXT_PUBLIC_API_URL. (Network Error)
```

This proved:
1. The new api client code was live on Vercel
2. `NEXT_PUBLIC_API_URL` was set in Vercel env vars to `https://hunar-assignment-production.up.railway.app`
3. So the earlier "no env var" issue was resolved

But the actual network call still failed.

---

## 5. Second Root Cause

Tested the Railway backend with `WebFetch`:
- `GET /` â†’ `{"message":"Hunar Voice Agents API","version":"1.0.0",...}` âœ…
- `GET /health` â†’ `{"status":"healthy"}` âœ…
- `GET /docs` â†’ Swagger UI âœ…

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

**No `Access-Control-Allow-Origin` header.** Classic CORS preflight failure â€” browser kills the real request, displays "Network Error".

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

- **Tighten CORS** â€” once a stable production Vercel URL exists, replace `https://*.vercel.app` with the exact origin.
- **Stable backend URL** â€” Railway's auto-generated subdomain works, but a custom domain is friendlier.
- **Same for `FRONTEND_URL` in Railway env** â€” set it to the Vercel URL as a belt-and-braces fallback alongside the wildcard.

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
| 1 | `/health`, `/`, `/api/agents/`, `/api/campaigns/`, `/api/candidates/` | âœ… Backend healthy; 1 existing agent (`Test Agent`, hunar_id `7d21ae42-â€¦`); 0 campaigns; 0 candidates |
| 2 | `POST /api/people/search` (Apollo key absent) | âœ… Returns `source: "mock"` with filtered mock candidates (Bangalore + senior) â€” graceful fallback works |
| 3 | `POST /api/campaigns/` + `POST /api/candidates/bulk` | âœ… Created `E2E Test Campaign` (id `78d4492d-â€¦`) + 3 candidates. **Bug found:** the bulk endpoint requires `campaign_id` on each item even though it uses the top-level one. Documented but not fixed (router is happy, only the schema rejects). |
| 4 | Webhook ingestion (simulated Hunar callbacks) | âš ï¸ Railway `HUNAR_WEBHOOK_SECRET` does **not** match the value user pasted. Verified locally (with same secret) that the signing algorithm is correct â€” `HMAC-SHA256(secret, "{ts}." + body)` base64-encoded. Local test fully passed: Aarav row updated to `status=COMPLETED, interest=Yes, qualified=Yes, recording_url=â€¦, call_result={â€¦}`. **Action for user:** re-check the `HUNAR_WEBHOOK_SECRET` in the Railway Variables tab; the value pasted (`7f271e8ef2d6â€¦`) rejects with 401. |
| 5 | Dashboard counters on production | âœ… Match live DB: 1 agent, 1 campaign, 3 candidates, 0 completed. |
| 6 | `PROBLEM3.md` | âœ… Written. Was referenced by `README.md` but didn't exist. Multi-channel design: voice AI (Hunar) as default + biometrics + SMS + supervisor fallback + LLM-driven daily reconciliation. |

### Files added
- `PROBLEM3.md` â€” conceptual answer for Problem 3 of the assignment brief
- `scripts/snapshot_prod.py` â€” small diagnostic that prints the Dashboard counters from the live Railway backend (used during E2E)

### New follow-up items
- **Bulk candidates schema** â€” drop the per-item `campaign_id` requirement, or document it on the frontend. Tracked in the bulk-call test failure above.
- **Railway `HUNAR_WEBHOOK_SECRET` mismatch** â€” user to re-verify the env var on the Railway dashboard. The pasted value rejects with 401 on production but works locally with the same code.
- **Campaign `total_candidates` denormalised column** â€” only set on launch. Dashboard shows `0` for un-launched campaigns even though the live `stats.total` is correct. Minor cosmetic; harmless if launch always happens before the user looks at the dashboard.

# Session Log — 2026-09-06

> Reviewing the implementation of the Hunar AI Hiring Assistant (FastAPI + Next.js) after deployment, and discussing whether any fixes are required before submission.

---

## 1. Initial Request

User asked for a full review of the implementation. The assignment brief (from Bhumika, HR Team Hunar.ai) was for:
1. AI Hiring Assistant (Voice AI Agents from Hunar.AI)
2. People Search & Reachout (using PDL, Apollo.IO, Proxycurl, or Coresignal)
3. Attendance tracking for 1000 people across 100 locations without smartphones, but with LLMs

Submission requirements: deployed solution link, GitHub repository, Python/Node.js/TypeScript/React.js/Next.js/shadcn/ui, deadline 2026-09-07 4:32 PM IST. Deployed URL: https://hunar-assignment-nine.vercel.app/

---

## 2. Code Review Performed

### Files inspected
- README.md — Project structure, tech stack (FastAPI + Next.js 15), setup, env vars, API endpoints, demo/live mode description
- REVIEW.md — Self-review document already present in the repo (~7.5/10 rating)
- PROBLEM3.md — 10-section conceptual design for attendance without smartphones
- ackend/src/main.py — FastAPI app with CORS configured to allow Vercel origins via regex
- ackend/src/config.py — Pydantic settings for HUNAR_API_KEY, APOLLO_API_KEY, DATABASE_URL, HUNAR_WEBHOOK_SECRET, FRONTEND_URL
- ackend/src/database.py — SQLAlchemy engine + session factory
- ackend/src/services/hunar_client.py — HTTP client for Hunar Voice Agents API (agents, calls, numbers)
- ackend/src/routers/campaigns.py — Campaign CRUD, launch with retry_config normalization (max_retry_count, retry_interval_hours)
- ackend/src/routers/people.py — Apollo.io people search with mock fallback (10 mock candidates)
- ackend/src/routers/webhooks.py — HMAC-validated webhook receiver that updates candidate status
- ackend/scripts/seed_demo_data.py — Idempotent demo seed: 4 agents, 3 campaigns, 128 candidates, 94 completed, 31 qualified, 47 interested
- rontend/src/app/page.tsx — Dashboard with stats cards, Quick Start Guide, "What is Hunar?" panel
- rontend/src/app/people/page.tsx — 3-step flow: Describe role ? Select candidates ? AI reachout
- rontend/src/app/results/page.tsx — Summary tiles, 3 charts (status, interest, 14-day trend), candidate cards
- rontend/src/app/attendance/page.tsx — 7-step architecture diagram, 4 channels, 30-day rollout plan
- rontend/src/lib/api.ts — Axios client with error normalization interceptor
- rontend/src/types/index.ts — Strongly-typed Hunar/Campaign/Candidate/Apollo interfaces
- rontend/tsconfig.json — Strict TypeScript, allowJs, noEmit (type-check only)
- rontend/package.json — Next.js 16.3.4, React 19, TypeScript 5, shadcn/ui via base-ui, recharts, sonner

### Architecture assessment

**Strengths:**
- Clean separation: outers/ (API layer), services/ (external integrations), models/ (ORM), schemas/ (Pydantic)
- Strong type safety across both backend and frontend
- HMAC-SHA256 webhook signature validation with timestamp check
- CORS configured via regex for https://*.vercel.app (with comment explaining the gotcha)
- Apollo client gracefully falls back to mock data when APOLLO_API_KEY is unset
- Demo seed script writes directly to DB — no live API call required
- Settings endpoint masks secrets (only shows prefix + length)
- /api/_debug/settings endpoint exists for Railway debugging (returns full traceback)

**Initial concerns raised in review:**
1. README mentioned "Frontend coming in Phase 3" while app was already deployed
2. /api/_debug/settings should be removed for production
3. Binary .db files (pp.db, hunar.db) appear to be committed
4. Sidebar shows "v1.0.0" with no clear versioning
5. Earlier REVIEW.md (self-written) said dashboard was empty — but that was outdated

---

## 3. Frontend Stack Verification

User asked: *"Please use TypeScript instead of plain JavaScript."*

Verified: all source files are already .ts / .tsx:
- 12 pp/**/page.tsx files
- 19 components/ui/*.tsx files
- 2 custom components (pp-sidebar.tsx, esults-charts.tsx)
- lib/api.ts, lib/utils.ts, 	ypes/index.ts

The only .js files in the repo are in .next/ (Next.js build output — expected). 	sconfig.json has strict: true and llowJs: true but no .js files in src/. **No code changes required.**

---

## 4. Deployed App Review (via screenshots)

User shared 9 screenshots of the live deployment at https://hunar-assignment-nine.vercel.app/:

### Image #1 — Dashboard
- Shows: 6 Total Agents, 4 Total Campaigns, 131 Total Candidates, 0 Calls Completed
- "Demo Environment" badge visible (confirms seed ran)
- Quick Start Guide with 5 numbered steps
- "What is Hunar?" panel with "Live status: Connected to backend"

### Image #2 — Voice Agents
- 6 agents displayed: Test Agent, Tech Sourcing Specialist, Demo Recruiter Agent, Demo Senior Screener, Demo Multilingual Screener, Demo Volume Caller
- Each card shows voice persona, language, persona name, prompt preview, truncated Hunar ID

### Image #3 — Campaigns
- 4 campaigns: E2E Test Campaign (DRAFT, 0 candidates), Q4 Engineering Hiring (RUNNING, 48 candidates), Senior Data Science Search (LAUNCHED, 36 candidates), Product Manager Pipeline (DRAFT, 44 candidates)
- Progress bars at 0% (correct since no real Hunar calls were made)
- Status badges, "Launch campaign" / "View details" buttons

### Image #4 — Candidates
- 100 candidates listed (Aarav Sharma, Rahul Verma, Sneha Kapoor, Varun Chatterjee, Pradeep Mehta, Tanvi Kumar, Ananya Kumar, etc.)
- Real Indian names, phone numbers, emails, campaign IDs
- Status badges: PENDING, COMPLETED, with "Interested: Yes/No" inline labels
- Search bar and status filter at top

### Image #5 — People Search (initial)
- 3-step flow strip: Describe role ? Select candidates ? AI reachout
- Pre-filled job description, job title, seniority, location fields
- Empty state with user icon

### Image #6 — People Search (with results)
- Successfully returned 1 candidate (Aarav Sharma) using mock fallback
- "Apollo mock dataset" badge in top-right
- "Found 1 candidate (mock data)" toast notification
- Step 1 marked Complete (green), Step 2 active, Step 3 pending
- Campaign selector dropdown + "Import selected (1)" button

### Image #7 — Attendance (Problem 3)
- "Problem 3" and "Conceptual architecture" badges
- 7-step architecture diagram (Employee ? Local device ? Gateway ? LLM reconciliation ? Ledger ? HR)
- Multi-channel design: Outbound AI voice call (~70%), Biometric/RFID kiosk (~20%), SMS/IVR (~8%), Supervisor fallback (~2%)
- Each channel shows percentage share and "where" use case

### Image #8 — Results
- Summary tiles: 90 Completed, 68 With results, 25 Interested, 25 Qualified
- 3 charts: Calls by status, Interest breakdown, 14-day trend
- **Bug observed:** first 3 visible cards (Aarav Sharma, Rahul Verma, Sneha Kapoor) all show "Pending" status despite 90 completed summary
- Root cause: API returns candidates in insertion order, not ordered by status/recency

### Image #9 — Settings
- "All systems operational" banner
- Database: PostgreSQL on Neon (ep-rapid-base), connected
- App metadata: Hunar Voice Agents API v1.0.0, debug enabled, frontend URL, webhook URL
- Integrations: Hunar Voice API (length 71), Apollo.io (length 22), Hunar Webhook Secret (length 65)
- All marked "configured" with masked previews

---

## 5. Issues Identified (Prioritized)

### P0 — Should fix before submission

**Issue #1: Dashboard "Calls Completed" shows 0**
- Dashboard counts campaigns.results[].stats.completed but the list_campaigns endpoint in ackend/src/routers/campaigns.py doesn't compute stats (only get_campaign does)
- Fix: add _compute_stats call inside the list endpoint loop, or count from candidates table directly

**Issue #2: Results page shows "Pending" cards first**
- The candidates list is returned in insertion order, so pending candidates appear at the top
- Fix in ackend/src/routers/candidates.py: add order_by(desc(Candidate.status == "COMPLETED"), desc(Candidate.updated_at))

### P1 — Should consider

**Issue #3: /api/_debug/settings endpoint in production**
- Exposes full tracebacks and internal paths; was meant for Railway debugging
- File: ackend/src/main.py
- Fix: remove the route (or gate behind a DEBUG flag)

**Issue #4: README references outdated state**
- Old draft mentioned "Frontend coming in Phase 3"
- File: README.md
- Fix: review and update to reflect the deployed state

### P2 — Cosmetic

**Issue #5: Sidebar version label**
- Currently shows "Hunar AI Hiring" + "v1.0.0" with "Demo Environment" below
- Cosmetic only — not a blocker

---

## 6. Final Recommendation

User asked: *"so do we need to fix anything at there??"*

Answer: **Only the two P0 issues** (Dashboard "0 Calls Completed" and Results page ordering). These are the only visible bugs an evaluator will notice on first load. The current implementation is at **8/10** — fixing those two brings it to **9/10**.

No code changes were made in this session — user explicitly requested review only, and the side-conversation boundary prevents file mutations without explicit approval.

---

## 7. User Instruction (Final)

User asked: *"keep all this chat history in session.md file"*

This entry documents the full 2026-09-06 review session. The existing 2026-09-05 log (Network Error debugging) is preserved above.
