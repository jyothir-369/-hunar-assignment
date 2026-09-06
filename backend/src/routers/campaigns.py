"""Campaign endpoints — grouping agents and candidates, and launching bulk calls."""

from collections import defaultdict
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.models.agent import Agent
from src.models.campaign import Campaign
from src.models.candidate import Candidate
from src.schemas.campaign import (
    CampaignCreate,
    CampaignLaunch,
    CampaignListResponse,
    CampaignResponse,
    CampaignStats,
    CampaignUpdate,
)
from src.services.hunar_client import HunarAPIError, HunarClient

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])


def _build_webhook_url() -> str:
    """Return the public HTTPS URL where Hunar should deliver callbacks.

    Hunar requires ``https://`` URLs. If HUNAR_WEBHOOK_URL is set (preferred for
    production), use it directly. Otherwise fall back to upgrading FRONTEND_URL
    to https — this is only useful when the request is being made from a public
    tunnel/proxy.
    """
    explicit = (settings.HUNAR_WEBHOOK_URL or "").strip()
    if explicit:
        return explicit.rstrip("/") + "/webhooks/hunar"
    frontend = settings.FRONTEND_URL.strip()
    if frontend.lower().startswith("http://"):
        frontend = "https://" + frontend[len("http://") :]
    return frontend.rstrip("/") + "/webhooks/hunar"


def _normalize_retry_config(retry_config: dict[str, Any] | None) -> dict[str, Any] | None:
    """Translate the local retry config keys to the keys Hunar expects.

    Local keys (per phase-2a docs): ``max_retries``, ``retry_interval_minutes``.
    Hunar API keys: ``max_retry_count``, ``retry_interval_hours``.

    Hunar only accepts these specific values for ``retry_interval_hours``:
    ``[3, 6, 9, 12, 24]``. We round the local value up to the next valid one.
    """
    if not retry_config:
        return None
    out: dict[str, Any] = {}
    if "max_retries" in retry_config:
        out["max_retry_count"] = retry_config["max_retries"]
    if "max_retry_count" in retry_config:
        out["max_retry_count"] = retry_config["max_retry_count"]
    if "retry_interval_minutes" in retry_config:
        hours = retry_config["retry_interval_minutes"] / 60
        out["retry_interval_hours"] = _snap_hours(hours)
    if "retry_interval_hours" in retry_config:
        out["retry_interval_hours"] = _snap_hours(
            float(retry_config["retry_interval_hours"])
        )
    # Pass through any Hunar-native fields the caller already set correctly
    for key, value in retry_config.items():
        if key in {"max_retry_count", "retry_interval_hours"}:
            continue
        out[key] = value
    # Hunar requires both fields when retry_config is present
    out.setdefault("max_retry_count", 1)
    out.setdefault("retry_interval_hours", 24)
    return out


_HUNAR_VALID_HOURS = (3, 6, 9, 12, 24)


def _snap_hours(hours: float) -> int:
    """Round ``hours`` up to the next valid Hunar value (3, 6, 9, 12, 24)."""
    for valid in _HUNAR_VALID_HOURS:
        if hours <= valid:
            return valid
    return _HUNAR_VALID_HOURS[-1]


def _stats_from_statuses(statuses: list[str]) -> CampaignStats:
    """Build a CampaignStats from a flat list of candidate status strings.

    Used by the list endpoint, which only needs status values to compute the
    tile counts. Avoids materializing full Candidate rows.
    """
    return CampaignStats(
        total=len(statuses),
        pending=sum(1 for s in statuses if s == "PENDING"),
        initiated=sum(1 for s in statuses if s == "INITIATED"),
        in_progress=sum(1 for s in statuses if s == "IN_PROGRESS"),
        completed=sum(1 for s in statuses if s == "COMPLETED"),
        not_connected=sum(1 for s in statuses if s == "NOT_CONNECTED"),
        failed=sum(1 for s in statuses if s in ("FAILED", "CANCELLED")),
    )


def _compute_stats(candidates: list[Candidate]) -> CampaignStats:
    return _stats_from_statuses([c.status for c in candidates])


def _attach_stats(
    db: Session, campaigns: list[Campaign]
) -> None:
    """Compute and attach per-campaign stats in a single query.

    The dashboard's "Calls Completed" tile and the campaign list response rely
    on each campaign carrying a ``stats`` object. Without this, list responses
    serialize ``stats: null`` and the dashboard reduce always returns 0.
    """
    if not campaigns:
        return
    campaign_ids = [c.id for c in campaigns]
    rows = (
        db.execute(
            select(Candidate.campaign_id, Candidate.status).where(
                Candidate.campaign_id.in_(campaign_ids)
            )
        )
        .all()
    )
    buckets: dict[str, list[str]] = defaultdict(list)
    for campaign_id, status in rows:
        buckets[campaign_id].append(status)
    for campaign in campaigns:
        campaign.stats = _stats_from_statuses(  # type: ignore[attr-defined]
            buckets.get(campaign.id, [])
        )


@router.get("/", response_model=CampaignListResponse)
def list_campaigns(
    page: int = 1,
    page_size: int = 10,
    campaign_status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> CampaignListResponse:
    stmt = select(Campaign)
    if campaign_status:
        stmt = stmt.where(Campaign.status == campaign_status)

    total = len(db.execute(stmt).scalars().all())
    rows = (
        db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    _attach_stats(db, rows)
    return CampaignListResponse(count=total, results=rows)


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    campaign_data: CampaignCreate, db: Session = Depends(get_db)
) -> Campaign:
    agent = db.get(Agent, campaign_data.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    campaign = Campaign(
        name=campaign_data.name,
        agent_id=campaign_data.agent_id,
        job_title=campaign_data.job_title,
        job_description=campaign_data.job_description,
        guardrails=campaign_data.guardrails or {},
        retry_config=campaign_data.retry_config or {},
        timezone=campaign_data.timezone or "Asia/Kolkata",
        status="DRAFT",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: str, db: Session = Depends(get_db)) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    candidates = list(
        db.execute(
            select(Candidate).where(Candidate.campaign_id == campaign_id)
        )
        .scalars()
        .all()
    )
    campaign.stats = _compute_stats(candidates)  # type: ignore[attr-defined]
    return campaign


@router.post("/{campaign_id}/launch", response_model=CampaignResponse)
def launch_campaign(
    campaign_id: str,
    launch_data: CampaignLaunch,
    db: Session = Depends(get_db),
) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == "LAUNCHED":
        raise HTTPException(status_code=400, detail="Campaign already launched")

    agent = db.get(Agent, campaign.agent_id)
    if not agent:
        raise HTTPException(status_code=400, detail="Campaign has no valid agent")

    candidates: list[Candidate] = list(
        db.execute(
            select(Candidate).where(
                Candidate.campaign_id == campaign_id,
                Candidate.status == "PENDING",
            )
        )
        .scalars()
        .all()
    )
    if not candidates:
        raise HTTPException(status_code=400, detail="No pending candidates to call")

    callback_config: dict[str, str] = {
        "call_status_callback_url": _build_webhook_url(),
        "call_recording_callback_url": _build_webhook_url(),
        "call_result_callback_url": _build_webhook_url(),
        "call_summary_callback_url": _build_webhook_url(),
    }

    call_rows: list[dict[str, Any]] = [
        {
            "callee_name": c.callee_name,
            "mobile_number": c.mobile_number,
            "custom_data": c.custom_data or {},
        }
        for c in candidates
    ]

    hunar = HunarClient()
    try:
        hunar_response = hunar.create_bulk_calls(
            agent_id=agent.hunar_agent_id,
            data=call_rows,
            request_id=f"campaign-{campaign_id}",
            retry_config=_normalize_retry_config(
                launch_data.retry_config or campaign.retry_config
            ),
            guardrails=launch_data.guardrails or campaign.guardrails,
            timezone=launch_data.timezone or campaign.timezone,
            callback_config=callback_config,
        )
    except HunarAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    # The Hunar bulk endpoint may return either a list of call objects or a
    # wrapper dict. Normalize before iterating.
    if isinstance(hunar_response, dict):
        hunar_calls = hunar_response.get("calls") or hunar_response.get("results") or []
    else:
        hunar_calls = hunar_response or []

    for candidate, call in zip(candidates, hunar_calls):
        if isinstance(call, dict):
            candidate.hunar_call_id = call.get("id")
        candidate.status = "INITIATED"
        candidate.request_id = f"campaign-{campaign_id}"

    campaign.status = "LAUNCHED"
    campaign.total_candidates = len(candidates)
    db.commit()
    db.refresh(campaign)

    candidates_all = list(
        db.execute(select(Candidate).where(Candidate.campaign_id == campaign_id))
        .scalars()
        .all()
    )
    campaign.stats = _compute_stats(candidates_all)  # type: ignore[attr-defined]
    return campaign


@router.put("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: str,
    campaign_data: CampaignUpdate,
    db: Session = Depends(get_db),
) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    for field, value in campaign_data.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)

    db.commit()
    db.refresh(campaign)
    return campaign
