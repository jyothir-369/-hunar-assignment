"""Candidate endpoints — add, list, bulk-create, and CSV upload."""

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.campaign import Campaign
from src.models.candidate import Candidate
from src.schemas.candidate import (
    CandidateBulkCreate,
    CandidateCreate,
    CandidateListResponse,
    CandidateResponse,
    CandidateUploadResponse,
)

router = APIRouter(prefix="/api/candidates", tags=["Candidates"])


@router.get("/", response_model=CandidateListResponse)
def list_candidates(
    campaign_id: Optional[str] = None,
    candidate_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> CandidateListResponse:
    stmt = select(Candidate)
    if campaign_id:
        stmt = stmt.where(Candidate.campaign_id == campaign_id)
    if candidate_status:
        stmt = stmt.where(Candidate.status == candidate_status)

    total = len(db.execute(stmt).scalars().all())
    rows = (
        db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    return CandidateListResponse(count=total, results=rows)


@router.post("/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(
    candidate_data: CandidateCreate, db: Session = Depends(get_db)
) -> Candidate:
    if not db.get(Campaign, candidate_data.campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")

    candidate = Candidate(
        campaign_id=candidate_data.campaign_id,
        callee_name=candidate_data.callee_name,
        mobile_number=candidate_data.mobile_number,
        email=candidate_data.email,
        custom_data=candidate_data.custom_data,
        status="PENDING",
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
def bulk_create_candidates(
    bulk_data: CandidateBulkCreate, db: Session = Depends(get_db)
) -> dict:
    if not db.get(Campaign, bulk_data.campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")

    created: list[Candidate] = []
    for c in bulk_data.candidates:
        candidate = Candidate(
            campaign_id=bulk_data.campaign_id,
            callee_name=c.callee_name,
            mobile_number=c.mobile_number,
            email=c.email,
            custom_data=c.custom_data,
            status="PENDING",
        )
        db.add(candidate)
        created.append(candidate)
    db.commit()
    return {"created": len(created), "candidate_ids": [c.id for c in created]}


@router.post(
    "/upload-csv", response_model=CandidateUploadResponse, status_code=status.HTTP_201_CREATED
)
async def upload_csv(
    campaign_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> CandidateUploadResponse:
    if not db.get(Campaign, campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    raw = await file.read()
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(decoded))
    required = {"callee_name", "mobile_number"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must include columns: {sorted(required)}",
        )

    created = 0
    errors: list[str] = []
    for index, row in enumerate(reader, start=1):
        callee_name = (row.get("callee_name") or "").strip()
        mobile_number = (row.get("mobile_number") or "").strip()
        if not callee_name or not mobile_number:
            errors.append(f"row {index}: missing callee_name or mobile_number")
            continue

        candidate = Candidate(
            campaign_id=campaign_id,
            callee_name=callee_name,
            mobile_number=mobile_number,
            email=(row.get("email") or "").strip() or None,
            custom_data={
                k: v
                for k, v in row.items()
                if k not in {"callee_name", "mobile_number", "email"}
            },
            status="PENDING",
        )
        db.add(candidate)
        created += 1

    db.commit()
    return CandidateUploadResponse(created=created, errors=errors)


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(candidate_id: str, db: Session = Depends(get_db)) -> None:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db.delete(candidate)
    db.commit()
    return None
