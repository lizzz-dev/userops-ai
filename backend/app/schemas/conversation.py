from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ConversationStatus = Literal[
    "idle",
    "collecting_fields",
    "awaiting_clarification",
    "awaiting_confirmation",
    "completed",
    "cancelled",
]


class ConversationContext(BaseModel):
    """Current public conversation state returned to the frontend."""

    status: ConversationStatus
    current_intent: str | None = None
    awaiting_field: str | None = None
    selected_user_id: int | None = None
    selected_user: dict[str, Any] | None = None
    draft_fields: dict[str, Any] = Field(default_factory=dict)
    candidate_count: int = Field(default=0, ge=0)
    pending_action: str | None = None
    ai_mode: Literal["openai", "fallback"] = "fallback"


class ConversationSuggestion(BaseModel):
    """Clickable suggestion displayed below an assistant response."""

    label: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)
    tone: Literal["default", "primary", "danger"] = "default"


class ConversationMessageResponse(BaseModel):
    """One saved user or assistant message."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    metadata: dict[str, Any] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationSummary(BaseModel):
    """Compact saved-conversation record used by the sidebar."""

    conversation_id: str
    title: str
    preview: str
    message_count: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """Saved conversations owned by the logged-in account."""

    conversations: list[ConversationSummary] = Field(default_factory=list)


class ConversationRenameRequest(BaseModel):
    """Validated custom title submitted from the sidebar."""

    title: str = Field(min_length=1, max_length=80)


class ConversationHistoryResponse(BaseModel):
    """Complete conversation data returned when restoring or resetting chat."""

    conversation_id: str
    context: ConversationContext
    messages: list[ConversationMessageResponse]