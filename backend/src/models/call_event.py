"""CallEvent ORM model — log of webhook events received from Hunar."""

import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.candidate import Candidate


class CallEvent(Base):
    """An immutable log entry for each webhook event received from Hunar."""

    __tablename__ = "call_events"

    id: Mapped[str] = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hunar_call_id: Mapped[str] = Column(String(255), nullable=False, index=True)
    candidate_id: Mapped[str | None] = Column(
        String(36), ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = Column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = Column(JSON, nullable=False, default=dict)
    received_at: Mapped[datetime] = Column(DateTime, nullable=False, default=datetime.utcnow)

    candidate: Mapped["Candidate | None"] = relationship("Candidate", back_populates="call_events")

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<CallEvent id={self.id} type={self.event_type} call_id={self.hunar_call_id}>"
