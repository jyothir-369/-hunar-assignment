"""Candidate ORM model."""

import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.campaign import Campaign
    from src.models.call_event import CallEvent


class Candidate(Base):
    """A candidate to be called as part of a campaign."""

    __tablename__ = "candidates"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id: Mapped[str] = Column(
        String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hunar_call_id: Mapped[str | None] = Column(String(255), nullable=True, index=True)
    callee_name: Mapped[str] = Column(String(255), nullable=False)
    mobile_number: Mapped[str] = Column(String(50), nullable=False)
    email: Mapped[str | None] = Column(String(255), nullable=True)
    custom_data: Mapped[dict[str, Any]] = Column(JSON, nullable=False, default=dict)
    status: Mapped[str] = Column(String(50), nullable=False, default="PENDING")
    interest_level: Mapped[str | None] = Column(String(50), nullable=True)
    qualification_status: Mapped[str | None] = Column(String(50), nullable=True)
    recording_url: Mapped[str | None] = Column(Text, nullable=True)
    call_result: Mapped[dict[str, Any] | None] = Column(JSON, nullable=True)
    request_id: Mapped[str | None] = Column(String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="candidates")
    call_events: Mapped[list["CallEvent"]] = relationship(
        "CallEvent", back_populates="candidate", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Candidate id={self.id} name={self.callee_name!r} status={self.status}>"
