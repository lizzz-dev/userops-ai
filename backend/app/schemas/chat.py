from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.assistant import AssistantInterpretation
from app.schemas.conversation import (
    ConversationContext,
    ConversationSuggestion,
)

ChatStatus = Literal[
    "success",
    "collecting_fields",
    "invalid",
    "not_found",
    "needs_clarification",
    "needs_confirmation",
    "cancelled",
    "error",
]


class ChatRequest(BaseModel):
    """
    Message sent from the frontend to the conversational assistant.

    conversation_id is optional for the first message.
    The backend creates a new conversation when it is missing.
    """

    message: str = Field(
        min_length=1,
        max_length=2000,
    )

    conversation_id: str | None = Field(
        default=None,
        min_length=36,
        max_length=36,
    )

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())

        if not cleaned:
            raise ValueError("Message cannot be empty.")

        return cleaned

    @field_validator("conversation_id", mode="before")
    @classmethod
    def clean_conversation_id(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None


class ParsedCommand(BaseModel):
    """
    Temporary compatibility model for the deterministic fallback parser.

    The final assistant primarily uses AssistantInterpretation,
    while this model remains available when AI is disabled or unavailable.
    """

    intent: Literal[
        "create",
        "read",
        "list",
        "count",
        "activity",
        "update",
        "delete",
        "unknown",
    ]

    email: str | None = None
    name: str | None = None
    user_id: int | None = None

    fields: dict[str, str] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class ChatAction(BaseModel):
    """
    Optional frontend action.

    The existing delete-confirmation button remains supported while
    natural-language confirmation is added through conversation state.
    """

    type: Literal["confirm_delete"]
    token: str
    label: str
    destructive: bool = True


class ChatActionResponse(BaseModel):
    """
    Complete response returned after each assistant message.
    """

    status: ChatStatus
    reply: str

    # Conversation continuity
    conversation_id: str | None = None
    context: ConversationContext | None = None

    # Clickable follow-up suggestions
    suggestions: list[ConversationSuggestion] = Field(
        default_factory=list,
    )

    # Structured AI understanding
    interpretation: AssistantInterpretation | None = None

    # Temporary fallback-parser information
    parsed: ParsedCommand | None = None

    # User record, list, count, activity, or other operation result
    data: (
        dict[str, Any]
        | list[dict[str, Any]]
        | None
    ) = None

    # Existing UI confirmation action
    action: ChatAction | None = None


class ConfirmActionRequest(BaseModel):
    """
    Confirmation sent by the existing delete-confirmation UI.
    """

    token: str = Field(min_length=1)
    confirm: bool
    conversation_id: str | None = Field(
        default=None,
        min_length=36,
        max_length=36,
    )