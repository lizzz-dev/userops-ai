from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AssistantIntent = Literal[
    "start_operation",
    "provide_information",
    "select_candidate",
    "confirm",
    "cancel",
    "switch_operation",
    "greeting",
    "help",
    "ask_context",
    "unknown",
]

AssistantOperation = Literal[
    "create",
    "read",
    "update",
    "delete",
    "list",
    "count",
    "activity",
    "none",
]

ReferenceType = Literal[
    "email",
    "name",
    "id",
    "current_user",
    "current_draft",
    "candidate",
    "none",
]

ControlAction = Literal[
    "continue",
    "confirm",
    "cancel",
    "skip",
    "reset",
    "none",
]

AssistantFieldName = Literal[
    "name",
    "email",
    "phone",
    "city",
    "none",
]


class AssistantFields(BaseModel):
    """
    User information extracted from a natural-language message.

    All fields are optional because a user may provide information
    over multiple messages.
    """

    name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    city: str | None = Field(default=None, max_length=100)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name", "email", "phone", "city", mode="before")
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = " ".join(str(value).strip().split())
        return cleaned or None


class AssistantInterpretation(BaseModel):
    """
    Structured interpretation produced by the AI or fallback parser.

    The AI only identifies meaning and extracted information.
    It does not directly create, update, or delete database records.
    """

    intent: AssistantIntent
    operation: AssistantOperation = "none"
    reference_type: ReferenceType = "none"

    # Direct user reference
    user_id: int | None = None

    # Candidate selection, for example:
    # "second one", "the other Ali", or "the Karachi one"
    ordinal: int | None = None
    candidate_hint: str | None = Field(default=None, max_length=200)

    # Field the user wants to provide or modify
    requested_field: AssistantFieldName = "none"

    # Information extracted from the message
    fields: AssistantFields = Field(default_factory=AssistantFields)

    # Conversation control
    control: ControlAction = "none"

    # How confident the interpreter is about the detected meaning
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Brief developer-readable explanation, not private reasoning
    explanation: str = Field(default="", max_length=300)

    model_config = ConfigDict(extra="forbid")

@field_validator("candidate_hint", mode="before")
@classmethod
def clean_candidate_hint(
    cls,
    value: str | None,
) -> str | None:
    if value is None:
        return None

    cleaned = " ".join(str(value).strip().split())
    return cleaned or None

@field_validator("explanation", mode="before")
@classmethod
def clean_explanation(
    cls,
    value: str | None,
) -> str:
    if value is None:
        return ""

    return " ".join(str(value).strip().split())