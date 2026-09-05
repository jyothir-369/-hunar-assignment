"""People search endpoint — Apollo.io with mock fallback."""

import logging
from typing import Literal, Optional

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/people", tags=["People"])


class PeopleSearchRequest(BaseModel):
    job_title: str = Field(..., min_length=1, max_length=200)
    seniority_levels: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=50)


class ApolloCandidate(BaseModel):
    apollo_id: str
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    seniority: Optional[str] = None


class PeopleSearchResponse(BaseModel):
    source: Literal["apollo", "mock"]
    candidates: list[ApolloCandidate]


MOCK_CANDIDATES: list[ApolloCandidate] = [
    ApolloCandidate(
        apollo_id="mock-001",
        name="Aarav Sharma",
        title="Senior Software Engineer",
        company="Razorpay",
        city="Bangalore",
        country="India",
        email="aarav.sharma@example.com",
        phone="+919876543210",
        linkedin_url="https://linkedin.com/in/aarav-sharma",
        seniority="senior",
    ),
    ApolloCandidate(
        apollo_id="mock-002",
        name="Priya Iyer",
        title="Engineering Manager",
        company="Swiggy",
        city="Bangalore",
        country="India",
        email="priya.iyer@example.com",
        phone="+919812345678",
        linkedin_url="https://linkedin.com/in/priya-iyer",
        seniority="manager",
    ),
    ApolloCandidate(
        apollo_id="mock-003",
        name="Rahul Verma",
        title="Software Engineer",
        company="Zerodha",
        city="Bangalore",
        country="India",
        email="rahul.verma@example.com",
        phone="+919898989898",
        linkedin_url="https://linkedin.com/in/rahul-verma",
        seniority="senior",
    ),
    ApolloCandidate(
        apollo_id="mock-004",
        name="Ananya Reddy",
        title="VP Engineering",
        company="Freshworks",
        city="Chennai",
        country="India",
        email="ananya.reddy@example.com",
        phone="+919876512340",
        linkedin_url="https://linkedin.com/in/ananya-reddy",
        seniority="vp",
    ),
    ApolloCandidate(
        apollo_id="mock-005",
        name="Vikram Patel",
        title="Director of Engineering",
        company="Postman",
        city="Bangalore",
        country="India",
        email="vikram.patel@example.com",
        phone="+919900112233",
        linkedin_url="https://linkedin.com/in/vikram-patel",
        seniority="director",
    ),
    ApolloCandidate(
        apollo_id="mock-006",
        name="Meera Nair",
        title="Junior Software Engineer",
        company="PhonePe",
        city="Bangalore",
        country="India",
        email="meera.nair@example.com",
        phone="+919811223344",
        linkedin_url="https://linkedin.com/in/meera-nair",
        seniority="entry",
    ),
    ApolloCandidate(
        apollo_id="mock-007",
        name="Karthik Menon",
        title="CTO",
        company="BrowserStack",
        city="Mumbai",
        country="India",
        email="karthik.menon@example.com",
        phone="+919845678901",
        linkedin_url="https://linkedin.com/in/karthik-menon",
        seniority="cxo",
    ),
    ApolloCandidate(
        apollo_id="mock-008",
        name="Sneha Kapoor",
        title="Senior Backend Engineer",
        company="Cred",
        city="Bangalore",
        country="India",
        email="sneha.kapoor@example.com",
        phone="+919855443322",
        linkedin_url="https://linkedin.com/in/sneha-kapoor",
        seniority="senior",
    ),
    ApolloCandidate(
        apollo_id="mock-009",
        name="Arjun Singh",
        title="Tech Lead",
        company="Meesho",
        city="Bangalore",
        country="India",
        email="arjun.singh@example.com",
        phone="+919733445566",
        linkedin_url="https://linkedin.com/in/arjun-singh",
        seniority="senior",
    ),
    ApolloCandidate(
        apollo_id="mock-010",
        name="Divya Krishnan",
        title="Staff Engineer",
        company="Flipkart",
        city="Bangalore",
        country="India",
        email="divya.krishnan@example.com",
        phone="+919922334455",
        linkedin_url="https://linkedin.com/in/divya-krishnan",
        seniority="senior",
    ),
]


def _filter_mock(
    job_title: str,
    seniority_levels: list[str],
    locations: list[str],
) -> list[ApolloCandidate]:
    """Filter the mock dataset by the requested criteria."""
    title_lower = job_title.lower()
    results: list[ApolloCandidate] = []
    for c in MOCK_CANDIDATES:
        if title_lower and c.title and title_lower not in c.title.lower():
            continue
        if seniority_levels and c.seniority not in seniority_levels:
            continue
        if locations:
            haystack = f"{c.city}, {c.country}".lower()
            if not any(loc.lower() in haystack for loc in locations):
                continue
        results.append(c)
    return results


async def _search_apollo(
    req: PeopleSearchRequest,
) -> Optional[list[ApolloCandidate]]:
    """Call Apollo's people search API. Returns None on any error."""
    if not settings.APOLLO_API_KEY:
        return None
    payload: dict = {
        "page": req.page,
        "per_page": req.per_page,
        "person_titles": [req.job_title],
    }
    if req.seniority_levels:
        payload["person_seniorities"] = req.seniority_levels
    if req.locations:
        payload["person_locations"] = req.locations
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.apollo.io/v1/mixed_people/search",
                json=payload,
                headers={**headers, "X-Api-Key": settings.APOLLO_API_KEY},
            )
        if resp.status_code != 200:
            logger.warning("Apollo returned %s: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
    except Exception as exc:
        logger.warning("Apollo request failed: %s", exc)
        return None

    people = data.get("people") or data.get("contacts") or []
    out: list[ApolloCandidate] = []
    for p in people[: req.per_page]:
        apollo_id = p.get("id") or p.get("apollo_id") or ""
        if not apollo_id:
            continue
        first = (p.get("first_name") or "").strip()
        last = (p.get("last_name") or "").strip()
        name = p.get("name") or f"{first} {last}".strip() or "Unknown"
        out.append(
            ApolloCandidate(
                apollo_id=str(apollo_id),
                name=name,
                title=p.get("title"),
                company=p.get("organization_name") or p.get("company"),
                city=p.get("city"),
                country=p.get("country"),
                email=p.get("email"),
                phone=p.get("phone_number") or p.get("mobile_number"),
                linkedin_url=p.get("linkedin_url"),
                seniority=p.get("seniority"),
            )
        )
    return out


@router.post("/search", response_model=PeopleSearchResponse)
async def search_people(req: PeopleSearchRequest) -> PeopleSearchResponse:
    """Search for people. Uses Apollo when APOLLO_API_KEY is set, else mock data."""
    apollo = await _search_apollo(req)
    if apollo is not None:
        return PeopleSearchResponse(source="apollo", candidates=apollo)

    filtered = _filter_mock(req.job_title, req.seniority_levels, req.locations)
    start = (req.page - 1) * req.per_page
    page = filtered[start : start + req.per_page]
    return PeopleSearchResponse(source="mock", candidates=page)
