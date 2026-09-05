"""Pydantic schemas for Campaign endpoints."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    agent_id: str
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    guardrails: Optional[dict[str, Any]] = None
    retry_config: Optional[dict[str, Any]] = None
    timezone: Optional[str] = "Asia/Kolkata"


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=255)
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    guardrails: Optional[dict[str, Any]] = None
    retry_config: Optional[dict[str, Any]] = None
    timezone: Optional[str] = None
    status: Optional[str] = None


class CampaignLaunch(BaseModel):
    guardrails: Optional[dict[str, Any]] = None
    retry_config: Optional[dict[str, Any]] = None
    timezone: Optional[str] = "Asia/Kolkata"


class CampaignStats(BaseModel):
    total: int = 0
    pending: int = 0
    initiated: int = 0
    in_progress: int = 0
    completed: int = 0
    not_connected: int = 0
    failed: int = 0


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    agent_id: str
    job_title: Optional[str]
    job_description: Optional[str]
    guardrails: dict[str, Any]
    retry_config: dict[str, Any]
    timezone: str
    status: str
    total_candidates: int
    stats: Optional[CampaignStats] = None
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    count: int
    results: list[CampaignResponse]
