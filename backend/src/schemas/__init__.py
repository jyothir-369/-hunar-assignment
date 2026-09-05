"""Pydantic schema package — re-exports all schemas for convenient imports."""

from src.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
)
from src.schemas.campaign import (
    CampaignCreate,
    CampaignLaunch,
    CampaignListResponse,
    CampaignResponse,
    CampaignStats,
    CampaignUpdate,
)
from src.schemas.candidate import (
    CandidateBulkCreate,
    CandidateCreate,
    CandidateListResponse,
    CandidateResponse,
    CandidateUploadResponse,
)
from src.schemas.webhook import WebhookPayload

__all__ = [
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
    "AgentListResponse",
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignLaunch",
    "CampaignStats",
    "CampaignResponse",
    "CampaignListResponse",
    "CandidateCreate",
    "CandidateBulkCreate",
    "CandidateResponse",
    "CandidateListResponse",
    "CandidateUploadResponse",
    "WebhookPayload",
]
