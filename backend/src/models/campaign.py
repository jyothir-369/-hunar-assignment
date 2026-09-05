"""Campaign ORM model."""

import uuid
from datetime import datetime
from typing import Any, List, TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.agent import Agent
    from src.models.candidate import Candidate


class Campaign(Base):
    """A hiring campaign that groups an agent and a list of candidates."""

    __tablename__ = "campaigns"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = Column(String(255), nullable=False)
    agent_id: Mapped[str] = Column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_title: Mapped[str | None] = Column(String(255), nullable=True)
    job_description: Mapped[str | None] = Column(Text, nullable=True)
    guardrails: Mapped[dict[str, Any]] = Column(JSON, nullable=False, default=dict)
    retry_config: Mapped[dict[str, Any]] = Column(JSON, nullable=False, default=dict)
    timezone: Mapped[str] = Column(String(100), nullable=False, default="Asia/Kolkata")
    status: Mapped[str] = Column(String(50), nullable=False, default="DRAFT")
    total_candidates: Mapped[int] = Column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    agent: Mapped["Agent"] = relationship("Agent", back_populates="campaigns")
    candidates: Mapped[List["Candidate"]] = relationship(
        "Candidate", back_populates="campaign", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Campaign id={self.id} name={self.name!r} status={self.status}>"
