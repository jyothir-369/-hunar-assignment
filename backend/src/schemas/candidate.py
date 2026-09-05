"""Pydantic schemas for Candidate endpoints."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CandidateCreate(BaseModel):
    campaign_id: str
    callee_name: str = Field(..., min_length=1)
    mobile_number: str = Field(..., pattern=r"^\+[1-9]\d{1,14}$")
    email: Optional[str] = None
    custom_data: dict[str, Any] = Field(default_factory=dict)


class CandidateBulkItem(BaseModel):
    """A single candidate inside ``CandidateBulkCreate``.

    The ``campaign_id`` is taken from the top-level payload, not the item —
    this avoids the per-item redundancy and the 422 it caused.
    """

    callee_name: str = Field(..., min_length=1)
    mobile_number: str = Field(..., pattern=r"^\+[1-9]\d{1,14}$")
    email: Optional[str] = None
    custom_data: dict[str, Any] = Field(default_factory=dict)


class CandidateBulkCreate(BaseModel):
    campaign_id: str
    candidates: list[CandidateBulkItem]


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    hunar_call_id: Optional[str]
    callee_name: str
    mobile_number: str
    email: Optional[str]
    custom_data: dict[str, Any]
    status: str
    interest_level: Optional[str]
    qualification_status: Optional[str]
    recording_url: Optional[str]
    call_result: Optional[dict[str, Any]]
    request_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class CandidateListResponse(BaseModel):
    count: int
    results: list[CandidateResponse]


class CandidateUploadResponse(BaseModel):
    created: int
    errors: list[str] = Field(default_factory=list)
