"""Pydantic schemas for Agent endpoints."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=64)
    voice_persona: str = Field(default="NEHA")
    persona_name: Optional[str] = None
    language: str = Field(default="ENGLISH")
    agent_prompt: str
    introduction: str
    objective: str = ""
    result_prompt: str = ""
    result_schema: dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=64)
    voice_persona: Optional[str] = None
    persona_name: Optional[str] = None
    language: Optional[str] = None
    agent_prompt: Optional[str] = None
    introduction: Optional[str] = None
    objective: Optional[str] = None
    result_prompt: Optional[str] = None
    result_schema: Optional[dict[str, Any]] = None
    status: Optional[str] = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    hunar_agent_id: str
    voice_persona: str
    persona_name: Optional[str]
    language: str
    agent_prompt: str
    introduction: str
    objective: Optional[str]
    result_prompt: Optional[str]
    result_schema: dict[str, Any]
    status: str
    summary: Optional[str]
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    count: int
    results: list[AgentResponse]
