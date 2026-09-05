"""Agent ORM model."""

import uuid
from datetime import datetime
from typing import Any, List, TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlalchemy.orm import Mapped, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.campaign import Campaign


class Agent(Base):
    """An AI calling agent created on the Hunar platform."""

    __tablename__ = "agents"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = Column(String(255), nullable=False)
    hunar_agent_id: Mapped[str] = Column(String(255), nullable=False, index=True)
    voice_persona: Mapped[str] = Column(String(50), nullable=False, default="NEHA")
    persona_name: Mapped[str | None] = Column(String(100), nullable=True)
    language: Mapped[str] = Column(String(50), nullable=False, default="ENGLISH")
    agent_prompt: Mapped[str] = Column(Text, nullable=False)
    introduction: Mapped[str] = Column(Text, nullable=False)
    objective: Mapped[str | None] = Column(Text, nullable=True)
    result_prompt: Mapped[str | None] = Column(Text, nullable=True)
    result_schema: Mapped[dict[str, Any]] = Column(JSON, nullable=False, default=dict)
    status: Mapped[str] = Column(String(20), nullable=False, default="ACTIVE")
    summary: Mapped[str | None] = Column(Text, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Agent id={self.id} name={self.name!r}>"
