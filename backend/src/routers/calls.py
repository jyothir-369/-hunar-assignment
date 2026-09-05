"""Calls endpoints — proxy to the Hunar API for live call status and results.

These endpoints don't persist anything: they forward a call_id to Hunar's
``GET /calls/{id}/`` and return whatever Hunar returns. The frontend uses them
to show the latest state of a call before the webhook lands, or to debug a
candidate whose webhook hasn't arrived yet.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.candidate import Candidate
from src.services.hunar_client import HunarAPIError, HunarClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calls", tags=["Calls"])


@router.get("/{call_id}")
def get_call(call_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return the live call object from the Hunar API.

    Optionally enrich with the local candidate (when the call_id is associated
    with one of our candidates) so the frontend doesn't have to make a second
    request.
    """
    hunar = HunarClient()
    try:
        call = hunar.get_call(call_id)
    except HunarAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    candidate: Optional[Candidate] = (
        db.query(Candidate).filter(Candidate.hunar_call_id == call_id).one_or_none()
    )
    response: dict[str, Any] = {"call": call, "candidate_id": None}
    if candidate is not None:
        response["candidate_id"] = candidate.id
        response["local_status"] = candidate.status
    return response


@router.get("/{call_id}/result")
def get_call_result(
    call_id: str, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Return the structured call result.

    If the call has already been recorded locally (i.e. the ``call_result_done``
    webhook has landed), prefer the local copy — it's what the agent returned,
    not a re-fetched copy that may lag by a few seconds. Otherwise proxy to
    Hunar.
    """
    candidate: Optional[Candidate] = (
        db.query(Candidate).filter(Candidate.hunar_call_id == call_id).one_or_none()
    )
    if candidate is not None and candidate.call_result:
        return {
            "source": "local",
            "candidate_id": candidate.id,
            "result": candidate.call_result,
            "interest_level": candidate.interest_level,
            "qualification_status": candidate.qualification_status,
        }

    hunar = HunarClient()
    try:
        call = hunar.get_call(call_id)
    except HunarAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    result = call.get("result") or {}
    return {
        "source": "hunar",
        "candidate_id": candidate.id if candidate else None,
        "result": result,
    }
