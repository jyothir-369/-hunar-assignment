"""Campaign endpoints — grouping agents and candidates, and launching bulk calls."""

import logging
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

logger = logging.getLogger(__name__)

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


# Status bucket names that ``CampaignStats`` exposes. Kept as a constant so a
# typo in either the SQL aggregation or the bucket counter fails immediately
# rather than silently producing 0 in the dashboard.
_STATUS_KEYS: tuple[str, ...] = (
    "pending",
    "initiated",
    "in_progress",
    "completed",
    "not_connected",
    "failed",
)


def _stats_from_statuses(statuses: list[str]) -> CampaignStats:
    """Build a CampaignStats from a flat list of candidate status strings.

    Both the list endpoint and the detail endpoint reduce to this helper, so
    the dashboard tile, the campaign detail panel, and any other consumer
    always see identical numbers.
    """
    bucket: dict[str, int] = {key: 0 for key in _STATUS_KEYS}
    for s in statuses:
        if s == "PENDING":
            bucket["pending"] += 1
        elif s == "INITIATED":
            bucket["initiated"] += 1
        elif s == "IN_PROGRESS":
            bucket["in_progress"] += 1
        elif s == "COMPLETED":
            bucket["completed"] += 1
        elif s == "NOT_CONNECTED":
            bucket["not_connected"] += 1
        elif s in ("FAILED", "CANCELLED"):
            bucket["failed"] += 1
    return CampaignStats(
        total=len(statuses),
        pending=bucket["pending"],
        initiated=bucket["initiated"],
        in_progress=bucket["in_progress"],
        completed=bucket["completed"],
        not_connected=bucket["not_connected"],
        failed=bucket["failed"],
    )


def _fetch_statuses_for_campaign(
    db: Session, campaign_id: str
) -> list[str]:
    """Return the candidate statuses for one campaign as a flat list.

    Used by the detail endpoint. The list endpoint uses the batched
    ``_attach_stats`` instead, which issues a single query for all visible
    campaigns.
    """
    return list(
        db.execute(
            select(Candidate.status).where(Candidate.campaign_id == campaign_id)
        )
        .scalars()
        .all()
    )


def _stats_for_campaign(db: Session, campaign_id: str) -> CampaignStats:
    """Compute stats for a single campaign.

    Single source of truth used by the detail endpoint. Returns a zero-filled
    CampaignStats (total=0) when the campaign has no candidates, instead of
    ``None``.
    """
    return _stats_from_statuses(_fetch_statuses_for_campaign(db, campaign_id))


def _attach_stats(
    db: Session, campaigns: list[Campaign]
) -> None:
    """Compute and attach per-campaign stats in a single batched query.

    The dashboard's "Calls Completed" tile and the campaign list response rely
    on each campaign carrying a populated ``stats`` object. Without this,
    list responses would serialize ``stats`` as an empty (but non-null)
    default and the dashboard reduce would always return 0.
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
    for campaign_id, statu in rows:
        buckets[campaign_id].append(statu)
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
    # New campaign has no candidates; attach an empty stats object so the
    # schema (now non-optional) serializes a real nested object instead of
    # falling back to the zero default.
    campaign.stats = CampaignStats()  # type: ignore[attr-defined]
    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: str, db: Session = Depends(get_db)) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.stats = _stats_for_campaign(db, campaign_id)  # type: ignore[attr-defined]
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

    # Hunar may legitimately return fewer rows than we sent (it drops
    # duplicates/invalid rows when remove_invalid_rows /
    # remove_duplicate_phone_numbers are enabled). Only mark the candidates we
    # actually got call objects for; log loudly if the counts diverge so the
    # desync is visible instead of silent.
    matched = min(len(candidates), len(hunar_calls))
    if matched < len(candidates):
        logger.warning(
            "Hunar returned %d call objects for %d candidates in campaign %s — "
            "%d candidate(s) left PENDING",
            len(hunar_calls),
            len(candidates),
            campaign_id,
            len(candidates) - matched,
        )
    for candidate, call in zip(candidates[:matched], hunar_calls[:matched]):
        if isinstance(call, dict):
            candidate.hunar_call_id = call.get("id")
        candidate.status = "INITIATED"
        candidate.request_id = f"campaign-{campaign_id}"

    campaign.status = "LAUNCHED"
    campaign.total_candidates = len(candidates)
    db.commit()
    db.refresh(campaign)

    campaign.stats = _stats_for_campaign(db, campaign_id)  # type: ignore[attr-defined]
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
    campaign.stats = _stats_for_campaign(db, campaign_id)  # type: ignore[attr-defined]
    return campaign
