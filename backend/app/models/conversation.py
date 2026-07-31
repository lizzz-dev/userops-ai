from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Conversation(Base):
    """
    Stores the current state of one account's chatbot conversation.

    This allows the assistant to remember:
    - the current operation
    - the user currently being discussed
    - incomplete user information
    - duplicate search candidates
    - pending confirmation actions
    """

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        default="idle",
        nullable=False,
    )

    current_intent: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    awaiting_field: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    selected_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    draft_fields: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    candidate_user_ids: Mapped[list[int]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    pending_action: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )