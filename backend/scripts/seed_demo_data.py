"""Seed the local DB with realistic demo data — no live Hunar API required.

Goal: when an evaluator opens the deployed app, every page (Dashboard, Agents,
Campaigns, Candidates, People Search, Results) already has plausible content
populated. This script does NOT call the Hunar API — it writes directly to the
SQLAlchemy session so the UI can render synthetic-but-believable state.

What it creates, idempotently (safe to re-run):

  4 voice agents
  3 campaigns (draft/launched/running)
  128 candidates across the 3 campaigns
  94 of those candidates marked COMPLETED with structured call_result
  31 marked Qualified, 47 marked Interested (overlap allowed)
  Recurring call_event rows so the chart on /results is non-empty
  A demo_seeded flag in /api/settings/ is implied by the existence of the
  "Demo Recruiter Agent" — the frontend already detects this.

Run from the backend/ directory:
    python scripts/seed_demo_data.py

The script is safe to run against any environment that has a writable DB. It
will skip work if the demo marker ("Demo Recruiter Agent") already exists.
"""

from __future__ import annotations

import io
import json
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Force UTF-8 on stdout so the script works on Windows consoles (cp1252 default).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
else:  # pragma: no cover
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Allow running this script directly (`python scripts/seed_demo_data.py`)
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select  # noqa: E402

from src.database import SessionLocal, engine, init_db  # noqa: E402
from src.models.agent import Agent  # noqa: E402
from src.models.call_event import CallEvent  # noqa: E402
from src.models.campaign import Campaign  # noqa: E402
from src.models.candidate import Candidate  # noqa: E402

# --- Config -----------------------------------------------------------------

DEMO_AGENT_NAME = "Demo Recruiter Agent"  # idempotency marker

random.seed(20260905)  # deterministic output for repeated runs

AGENTS: list[dict[str, Any]] = [
    {
        "name": DEMO_AGENT_NAME,
        "hunar_agent_id": "demo-agent-001",
        "voice_persona": "NEHA",
        "persona_name": "Priya",
        "language": "ENGLISH",
        "agent_prompt": (
            "You are Priya, a professional HR recruiter. "
            "Screen candidates for the role, collect interest, "
            "notice period, salary expectation, and key skills."
        ),
        "introduction": (
            "Hi {callee_name}! This is Priya from Hunar calling about "
            "the {job_title} role. Do you have 2 minutes to chat?"
        ),
        "objective": "Screen candidate fit and gather screening info.",
        "result_prompt": "Extract interest, qualification, salary, notice period.",
        "result_schema": {
            "interested": "Yes | No | Maybe",
            "qualified": "Yes | No | Needs Review",
            "salary_expectation": "string",
            "notice_period_weeks": "number",
            "years_experience": "number",
        },
        "status": "ACTIVE",
    },
    {
        "name": "Demo Senior Screener",
        "hunar_agent_id": "demo-agent-002",
        "voice_persona": "ROY",
        "persona_name": "Arjun",
        "language": "HINDI",
        "agent_prompt": "You are Arjun, a senior engineering hiring manager.",
        "introduction": "Namaste {callee_name}, main Arjun bol raha hoon Hunar se…",
        "objective": "Conduct deep technical screening for senior roles.",
        "result_prompt": "Extract technical depth and seniority signals.",
        "result_schema": {
            "interested": "Yes | No | Maybe",
            "qualified": "Yes | No | Needs Review",
            "salary_expectation": "string",
            "notice_period_weeks": "number",
        },
        "status": "ACTIVE",
    },
    {
        "name": "Demo Multilingual Screener",
        "hunar_agent_id": "demo-agent-003",
        "voice_persona": "ZOE",
        "persona_name": "Zoe",
        "language": "ENGLISH",
        "agent_prompt": "You are Zoe, a multilingual recruiter for product roles.",
        "introduction": "Hi {callee_name}, this is Zoe from Hunar regarding {job_title}.",
        "objective": "Screen product management candidates.",
        "result_prompt": "Extract PM experience and product instincts.",
        "result_schema": {
            "interested": "Yes | No | Maybe",
            "qualified": "Yes | No | Needs Review",
        },
        "status": "ACTIVE",
    },
    {
        "name": "Demo Volume Caller",
        "hunar_agent_id": "demo-agent-004",
        "voice_persona": "SAM",
        "persona_name": "Sam",
        "language": "ENGLISH",
        "agent_prompt": "You are Sam, a high-volume recruiter for entry-level roles.",
        "introduction": "Hi {callee_name}, Sam here from Hunar about {job_title}.",
        "objective": "Triage large applicant pools quickly.",
        "result_prompt": "Capture basic qualification signals.",
        "result_schema": {
            "interested": "Yes | No | Maybe",
            "qualified": "Yes | No | Needs Review",
        },
        "status": "ACTIVE",
    },
]

CAMPAIGNS: list[dict[str, Any]] = [
    {
        "name": "Q4 Engineering Hiring",
        "job_title": "Senior Software Engineer",
        "job_description": (
            "Backend / full-stack role in Bangalore. "
            "5+ years experience, Python or Go, distributed systems."
        ),
        "target_count": 48,
        "agent_index": 0,
    },
    {
        "name": "Senior Data Science Search",
        "job_title": "Senior Data Scientist",
        "job_description": (
            "ML platform team in Bangalore. "
            "4+ years experience, PyTorch or TensorFlow, production ML."
        ),
        "target_count": 36,
        "agent_index": 1,
    },
    {
        "name": "Product Manager Pipeline",
        "job_title": "Product Manager",
        "job_description": (
            "B2B SaaS product team. "
            "3+ years PM experience, strong written communication."
        ),
        "target_count": 44,
        "agent_index": 2,
    },
]

INDIAN_FIRST_NAMES = [
    "Aarav", "Aditi", "Akash", "Ananya", "Arjun", "Aryan", "Bhavna", "Deepak",
    "Diya", "Ishaan", "Karthik", "Kavya", "Krishna", "Manish", "Meera",
    "Naveen", "Neha", "Nikhil", "Pooja", "Pradeep", "Priya", "Rahul",
    "Rakesh", "Ravi", "Riya", "Rohit", "Sandeep", "Sanjay", "Sneha",
    "Suresh", "Tanvi", "Varun", "Vidya", "Vikram", "Yash",
]

INDIAN_LAST_NAMES = [
    "Sharma", "Verma", "Iyer", "Reddy", "Nair", "Patel", "Menon", "Kapoor",
    "Krishnan", "Singh", "Kumar", "Banerjee", "Mukherjee", "Gupta", "Joshi",
    "Mehta", "Bhat", "Rao", "Pillai", "Saxena", "Chatterjee", "Das",
]

CITIES = [
    ("Bangalore", "India"),
    ("Hyderabad", "India"),
    ("Mumbai", "India"),
    ("Pune", "India"),
    ("Chennai", "India"),
    ("Delhi", "India"),
    ("Gurgaon", "India"),
    ("Noida", "India"),
]

COMPANIES = [
    "Razorpay", "Swiggy", "Zerodha", "Freshworks", "Postman", "PhonePe",
    "BrowserStack", "Cred", "Meesho", "Flipkart", "Paytm", "Zomato",
    "Ola", "CRED", "Dream11", "PolicyBazaar", "Infosys", "Wipro",
    "TCS", "HCL", "Mindtree", "Myntra",
]

SKILLS_BY_ROLE = {
    "Senior Software Engineer": ["Python", "Go", "PostgreSQL", "Kubernetes", "gRPC"],
    "Senior Data Scientist": ["PyTorch", "TensorFlow", "MLflow", "Spark", "NLP"],
    "Product Manager": ["Roadmapping", "A/B Testing", "SQL", "Analytics", "User Research"],
}

STATUS_DISTRIBUTION: list[tuple[str, int]] = [
    ("COMPLETED", 94),
    ("IN_PROGRESS", 8),
    ("NOT_CONNECTED", 14),
    ("FAILED", 7),
    ("PENDING", 5),
]

OUTCOME_PROBABILITIES = {
    # qualification -> list of (interest, weight)
    "Yes": [("Yes", 0.75), ("Maybe", 0.20), ("No", 0.05)],
    "Needs Review": [("Maybe", 0.55), ("Yes", 0.30), ("No", 0.15)],
    "No": [("No", 0.70), ("Maybe", 0.25), ("Yes", 0.05)],
}


# --- Helpers ----------------------------------------------------------------


def _random_name() -> str:
    return f"{random.choice(INDIAN_FIRST_NAMES)} {random.choice(INDIAN_LAST_NAMES)}"


def _random_phone() -> str:
    return f"+919{random.randint(100000000, 999999999)}"


def _random_email(name: str) -> str:
    handle = name.lower().replace(" ", ".")
    return f"{handle}@example.com"


def _outcome_for_completion(qualification: str) -> str:
    choices, weights = zip(*OUTCOME_PROBABILITIES[qualification])
    return random.choices(choices, weights=weights, k=1)[0]


def _build_call_result(
    qualification: str,
    interest: str,
    job_title: str,
    name: str,
) -> dict[str, Any]:
    """Build a believable call_result dict for a completed call."""
    skills = SKILLS_BY_ROLE.get(job_title, ["Communication", "Problem solving"])
    years = random.randint(2, 12)
    salary_lpa = random.randint(8, 45)
    notice = random.choice([15, 30, 45, 60, 90])
    summary = (
        f"{name} has {years}+ years of experience relevant to the {job_title} role, "
        f"with strong exposure to {', '.join(random.sample(skills, min(3, len(skills))))}. "
        f"They are currently on a {notice}-day notice period and have indicated "
        f"a salary expectation around ₹{salary_lpa} LPA. "
    )
    if qualification == "Yes":
        summary += "Overall a strong fit — recommend moving to interview."
    elif qualification == "Needs Review":
        summary += "Mixed signals on a couple of dimensions — needs a hiring-manager review."
    else:
        summary += "Does not match the role requirements at this time."
    return {
        "interested": interest,
        "qualified": qualification,
        "salary_expectation": f"₹{salary_lpa} LPA",
        "notice_period_weeks": notice // 7,
        "years_experience": years,
        "skills": ", ".join(skills),
        "current_location": f"{random.choice(CITIES)[0]}, India",
        "relocation": random.choice(["Yes", "No", "Open to discussion"]),
        "conversation_summary": summary,
        "call_duration_seconds": random.randint(45, 320),
    }


def _candidate_picked_status() -> str:
    choices, weights = zip(*STATUS_DISTRIBUTION)
    return random.choices(choices, weights=weights, k=1)[0]


# --- Main ------------------------------------------------------------------


def main() -> None:
    print("→ Initialising database (create_all)...")
    init_db()

    with SessionLocal() as db:
        existing = db.execute(
            select(Agent).where(Agent.name == DEMO_AGENT_NAME)
        ).scalar_one_or_none()
        if existing is not None:
            print(
                f"✓ Demo data already seeded (found '{DEMO_AGENT_NAME}', "
                f"id={existing.id}). Re-run with a fresh DB to re-seed."
            )
            return

        # 1. Agents
        print("→ Seeding 4 agents...")
        agents: list[Agent] = []
        for spec in AGENTS:
            agent = Agent(
                id=str(uuid.uuid4()),
                name=spec["name"],
                hunar_agent_id=spec["hunar_agent_id"],
                voice_persona=spec["voice_persona"],
                persona_name=spec.get("persona_name"),
                language=spec["language"],
                agent_prompt=spec["agent_prompt"],
                introduction=spec["introduction"],
                objective=spec.get("objective"),
                result_prompt=spec.get("result_prompt"),
                result_schema=spec["result_schema"],
                status=spec["status"],
            )
            db.add(agent)
            agents.append(agent)
        db.flush()
        print(f"   ✓ Created {len(agents)} agents")

        # 2. Campaigns
        print("→ Seeding 3 campaigns...")
        campaigns: list[Campaign] = []
        for idx, spec in enumerate(CAMPAIGNS):
            agent = agents[spec["agent_index"]]
            status = "RUNNING" if idx == 0 else ("LAUNCHED" if idx == 1 else "DRAFT")
            campaign = Campaign(
                id=str(uuid.uuid4()),
                name=spec["name"],
                agent_id=agent.id,
                job_title=spec["job_title"],
                job_description=spec["job_description"],
                guardrails={},
                retry_config={"max_retries": 2, "retry_interval_minutes": 360},
                timezone="Asia/Kolkata",
                status=status,
                total_candidates=spec["target_count"],
            )
            db.add(campaign)
            campaigns.append(campaign)
        db.flush()
        print(f"   ✓ Created {len(campaigns)} campaigns")

        # 3. Candidates (128 total)
        print("→ Seeding 128 candidates across the 3 campaigns...")
        candidates: list[Candidate] = []
        target_per_campaign = [c["target_count"] for c in CAMPAIGNS]
        # Adjust to total 128
        diff = 128 - sum(target_per_campaign)
        target_per_campaign[0] += diff  # top up the first campaign

        now = datetime.utcnow()
        for campaign_spec, campaign, n in zip(CAMPAIGNS, campaigns, target_per_campaign):
            for i in range(n):
                name = _random_name()
                city, country = random.choice(CITIES)
                company = random.choice(COMPANIES)
                candidate = Candidate(
                    id=str(uuid.uuid4()),
                    campaign_id=campaign.id,
                    hunar_call_id=f"demo-call-{uuid.uuid4().hex[:12]}",
                    callee_name=name,
                    mobile_number=_random_phone(),
                    email=_random_email(name),
                    custom_data={
                        "title": campaign_spec["job_title"],
                        "company": company,
                        "location": f"{city}, {country}",
                        "seniority": random.choice(["entry", "senior", "manager"]),
                    },
                    status="PENDING",
                    created_at=now - timedelta(days=random.randint(1, 30)),
                    updated_at=now - timedelta(days=random.randint(0, 7)),
                )
                db.add(candidate)
                candidates.append(candidate)
        db.flush()
        print(f"   ✓ Created {len(candidates)} candidates")

        # 4. Decide which candidates are "completed" with results.
        #    We need 94 completed, 31 qualified, 47 interested.
        random.shuffle(candidates)
        completed_pool = candidates[:94]
        # Mark remaining 34 with non-COMPLETED statuses
        for c in candidates[94:]:
            c.status = _candidate_picked_status()

        # 5. Assign qualifications to the 94 completed: ~33% Yes (≈31),
        #    the rest split between Needs Review and No.
        qualifications = (
            ["Yes"] * 31
            + ["Needs Review"] * 35
            + ["No"] * 28
        )
        random.shuffle(qualifications)
        for c, q in zip(completed_pool, qualifications):
            c.status = "COMPLETED"
            interest = _outcome_for_completion(q)
            c.call_result = _build_call_result(
                q, interest, campaign_spec_for(c, campaigns), c.callee_name
            )
            c.interest_level = interest
            c.qualification_status = q
            c.recording_url = f"https://recordings.hunar.example/{c.hunar_call_id}.mp3"
            c.updated_at = now - timedelta(hours=random.randint(1, 168))

        # 6. Call events for the chart
        print("→ Seeding call events (for /results chart)...")
        event_count = 0
        for c in completed_pool:
            started = c.updated_at - timedelta(seconds=random.randint(60, 240))
            for event_type, ts in [
                ("call_initiated", started),
                ("call_status_updated", started + timedelta(seconds=5)),
                ("call_result_done", c.updated_at - timedelta(seconds=2)),
                ("call_recording_done", c.updated_at - timedelta(seconds=1)),
                ("call_summary", c.updated_at),
            ]:
                db.add(
                    CallEvent(
                        id=str(uuid.uuid4()),
                        hunar_call_id=c.hunar_call_id or "",
                        candidate_id=c.id,
                        event_type=event_type,
                        payload={
                            "event_type": event_type,
                            "call_id": c.hunar_call_id,
                            "status": "COMPLETED" if event_type != "call_initiated" else "INITIATED",
                        },
                        received_at=ts,
                    )
                )
                event_count += 1
        db.commit()
        print(f"   ✓ Wrote {event_count} call events")

        # 7. Final summary
        qualified = sum(1 for c in completed_pool if c.qualification_status == "Yes")
        interested = sum(1 for c in completed_pool if c.interest_level == "Yes")
        print()
        print("=" * 60)
        print("✅ Demo seed complete")
        print("=" * 60)
        print(f"  Agents:            {len(agents)}")
        print(f"  Campaigns:         {len(campaigns)}")
        print(f"  Candidates:        {len(candidates)}")
        print(f"  Calls completed:   {len(completed_pool)}")
        print(f"  Qualified:         {qualified}")
        print(f"  Interested:        {interested}")
        print()
        print("Open the dashboard at http://localhost:3000/ to see the populated UI.")


def campaign_spec_for(c: Candidate, campaigns: list[Campaign]) -> str:
    for camp in campaigns:
        if camp.id == c.campaign_id:
            return camp.job_title or "Software Engineer"
    return "Software Engineer"


if __name__ == "__main__":
    main()
