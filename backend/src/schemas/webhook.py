"""Pydantic schemas for webhook payloads."""

from typing import Any, Optional

from pydantic import BaseModel


class WebhookPayload(BaseModel):
    """Schema for Hunar webhook payloads (all fields optional to be permissive)."""

    event_type: str
    call_id: str
    agent_id: Optional[str] = None
    request_id: Optional[str] = None
    status: Optional[str] = None
    lifecycle_status: Optional[str] = None
    answered_by: Optional[str] = None
    recording_url: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    duration_seconds: Optional[float] = None
    duration_minutes: Optional[float] = None
    to_number: Optional[str] = None
    from_phone_number: Optional[str] = None
    max_retries: Optional[int] = None
    retry_count: Optional[int] = None
    retries_left: Optional[int] = None
    next_retry_scheduled_at: Optional[str] = None
    retry_reason: Optional[str] = None
    timezone: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
