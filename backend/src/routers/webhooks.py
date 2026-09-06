"""Webhook endpoints — receives Hunar callbacks, validates signatures, updates DB."""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.call_event import CallEvent
from src.models.candidate import Candidate
from src.utils.security import validate_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _find_candidate(
    db: Session, call_id: str | None, request_id: str | None
) -> Candidate | None:
    """Find the candidate matching a webhook by call id or request id."""
    if call_id:
        candidate = db.execute(
            select(Candidate).where(Candidate.hunar_call_id == call_id)
        ).scalar_one_or_none()
        if candidate:
            return candidate
    if request_id:
        # Many candidates can share one request_id (campaign launch stamps
        # ``campaign-{id}`` on every row), so use .first() — scalar_one_or_none()
        # would raise MultipleResultsFound and 500 the webhook.
        candidate = (
            db.execute(
                select(Candidate)
                .where(Candidate.request_id == request_id)
                .order_by(Candidate.created_at)
            )
            .scalars()
            .first()
        )
        if candidate:
            return candidate
    return None


def _apply_event(candidate: Candidate, event_type: str, payload: dict[str, Any]) -> None:
    """Update a candidate based on the webhook event type."""
    if event_type == "call_status_updated":
        status_value = payload.get("status") or payload.get("lifecycle_status")
        if status_value:
            candidate.status = status_value

    elif event_type == "call_recording_done":
        if payload.get("recording_url"):
            candidate.recording_url = payload["recording_url"]

    elif event_type == "call_result_done":
        result = payload.get("result") or {}
        if result:
            candidate.call_result = result
        if "interested" in result:
            candidate.interest_level = str(result["interested"])
        if "qualified" in result:
            candidate.qualification_status = str(result["qualified"])

    elif event_type == "call_summary":
        lifecycle = payload.get("lifecycle_status") or payload.get("status")
        if lifecycle:
            candidate.status = lifecycle
        if payload.get("recording_url"):
            candidate.recording_url = payload["recording_url"]
        result = payload.get("result")
        if result:
            candidate.call_result = result
            if isinstance(result, dict):
                if "interested" in result:
                    candidate.interest_level = str(result["interested"])
                if "qualified" in result:
                    candidate.qualification_status = str(result["qualified"])


@router.post("/hunar", status_code=status.HTTP_200_OK)
async def receive_hunar_webhook(
    request: Request, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Receive a Hunar webhook, validate the signature, and update the candidate."""
    body = await request.body()
    signature = request.headers.get("X-Hunar-Signature", "")
    timestamp = request.headers.get("X-Hunar-Timestamp", "")

    if not validate_signature(timestamp, body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload: dict[str, Any] = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    event_type = payload.get("event_type", "")
    call_id = payload.get("call_id", "")
    request_id = payload.get("request_id", "")

    event = CallEvent(
        hunar_call_id=call_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(event)

    candidate = _find_candidate(db, call_id, request_id)
    if candidate is not None:
        event.candidate_id = candidate.id
        _apply_event(candidate, event_type, payload)
    else:
        logger.warning(
            "Webhook for unknown call: call_id=%s request_id=%s event=%s",
            call_id,
            request_id,
            event_type,
        )

    db.commit()
    return {"ok": True, "event": event_type, "matched": candidate is not None}
