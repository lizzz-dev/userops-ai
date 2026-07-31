import json
import logging
import re
from typing import Iterable

from app.core.config import get_settings
from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage
from app.schemas.assistant import AssistantFields, AssistantInterpretation
from app.services.command_parser import (
    extract_city,
    extract_email,
    extract_phone,
    extract_user_id,
)


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are the language-understanding layer for UserOps AI, a focused user-management
assistant. Interpret the user's meaning using the current conversation state and recent
messages. Return only the structured AssistantInterpretation schema.

Supported operations: create, read, update, delete, list, count, activity.
Supported managed-user fields: name, email, phone, city, integer ID.

Rules:
- Understand natural paraphrases, typos, pronouns, follow-ups, and changed intentions.
- "her", "him", "she", "his", "that person" can refer to the selected user or current draft.
- "second one", "the other Ali", "the Karachi one" selects from presented candidates.
- "actually don't delete him" is cancellation, not an unknown command.
- "change her number instead" can cancel a pending delete and switch to update.
- Never invent a user, field value, or database result.
- If the user merely supplies information requested by the assistant, use
  intent=provide_information and operation equal to the active operation.
- If meaning is unclear, use unknown with low confidence.
- explanation must be a short description of the interpretation, not hidden reasoning.
""".strip()


CREATE_PATTERNS = [
    r"\b(?:add|create|creat|craete|register|regsiter|onboard|insert)\b",
    r"\b(?:new\s+(?:user|employee|person|member))\b",
    r"\b(?:we\s+have\s+(?:a\s+)?new)\b",
    r"\b(?:needs?\s+(?:an?\s+)?account)\b",
    r"\bshould\s+be\s+(?:added|registered|onboarded)\b",
]
READ_PATTERNS = [
    r"\b(?:show|shwo|find|fnd|get|display|view|lookup|look\s+up|search|serach)\b",
    r"\b(?:tell\s+me\s+about|details?\s+(?:for|of|about))\b",
    r"\bwhere\s+(?:is|are)\b",
]
UPDATE_PATTERNS = [
    r"\b(?:update|udpate|updae|change|chnage|modify|set|edit)\b",
    r"\b(?:moved|relocated)\s+to\b",
    r"\b(?:lives?|resides?)\s+in\b",
    r"\b(?:should\s+be|make\s+(?:it|that))\b",
]
DELETE_PATTERNS = [
    r"\b(?:delete|delte|delet|remove|remvoe|erase)\b",
    r"\b(?:get\s+rid\s+of)\b",
]
CANCEL_PATTERNS = [
    r"\b(?:cancel|stop|never\s*mind|nevermind)\b",
    r"\b(?:do\s+not|don't|dont)\s+(?:delete|remove|continue|do\s+that)\b",
    r"\b(?:leave\s+(?:it|the\s+record)\s+(?:alone|as\s+it\s+is))\b",
]
CONFIRM_PATTERNS = [
    r"^(?:yes|yep|yeah|confirm|confirmed|sure|okay|ok|go\s+ahead|do\s+it|continue)[.!\s]*$",
]
SKIP_PATTERNS = [
    (
        r"^(?:"
        r"skip(?:\s+(?:it|phone|city))?"
        r"|none"
        r"|not\s+now"
        r"|no\s+(?:phone|city)"
        r"|create(?:\s+(?:her|him|them|it|the\s+user|this\s+user))?\s+now"
        r")[.!\s]*$"
    ),
]


def _matches_any(patterns: Iterable[str], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _extract_ordinal(text: str) -> int | None:
    if re.search(r"\bnot\s+(?:the\s+)?first(?:\s+(?:one|result|user))?\b", text, re.I):
        return 2

    words = {
        "first": 1,
        "1st": 1,
        "one": 1,
        "second": 2,
        "2nd": 2,
        "two": 2,
        "third": 3,
        "3rd": 3,
        "three": 3,
        "fourth": 4,
        "4th": 4,
    }
    match = re.search(r"\b(first|1st|second|2nd|third|3rd|fourth|4th)\b", text, re.I)
    if match:
        return words[match.group(1).lower()]
    match = re.search(r"\b(?:option|number|result)?\s*(\d+)\b", text, re.I)
    if match:
        return int(match.group(1))
    if re.search(r"\b(?:the\s+)?other\s+(?:one|user|person|ali)?\b", text, re.I):
        return -1
    return None


def _clean_name(value: str) -> str:
    value = re.split(
        r"\s+(?:with|whose|who|and|email|phone|city|from|in)\b",
        value,
        maxsplit=1,
        flags=re.I,
    )[0]
    cleaned = " ".join(value.strip(" ,.;:'\"!?-").split())
    cleaned = re.sub(r"\s+(?:recently|now)$", "", cleaned, flags=re.I)
    cleaned = re.sub(
        r"\s+(?:user|person|employee|record)$",
        "",
        cleaned,
        flags=re.I,
    )
    return cleaned.strip()


def _extract_name(message: str, operation: str) -> str | None:
    normalized_message = message.strip().rstrip("?!.,;:")

    if extract_email(normalized_message) or extract_user_id(normalized_message) is not None:
        # A name may still exist, but email/ID is the safer reference.
        pass

    patterns: list[str] = []
    if operation == "create":
        patterns = [
            r"\b(?:called|named)\s+([A-Za-z][A-Za-z .'-]{0,100})",
            (
                r"\b(?:add|create|creat|craete|register|regsiter|onboard)\s+"
                r"(?:a\s+|the\s+)?(?:new\s+)?"
                r"(?:user\s+|employee\s+|person\s+)?"
                r"([A-Za-z][A-Za-z .'-]{0,100})"
            ),
            r"\bnew\s+(?:user|employee|person|member)\s+([A-Za-z][A-Za-z .'-]{0,100})",
            r"^([A-Za-z][A-Za-z .'-]{0,100}?)\s+needs?\s+(?:an?\s+)?account\b",
            r"^([A-Za-z][A-Za-z .'-]{0,100}?)\s+should\s+be\s+(?:added|registered|onboarded)\b",
        ]
    elif operation in {"read", "delete"}:
        patterns = [
            (
                rf"\b(?:show|shwo|find|fnd|get|display|view|lookup|look\s+up|search|"
                rf"serach|delete|delte|delet|remove|remvoe|erase)\s+"
                rf"(?:me\s+)?(?:the\s+)?(?:user\s+)?(?:named\s+)?"
                rf"([A-Za-z][A-Za-z .'-]{{0,100}})$"
            ),
            r"\bwhere\s+(?:is|are)\s+(?:the\s+)?(?:user\s+)?([A-Za-z][A-Za-z .'-]{0,100}?)(?:\s+user)?$",
            r"\b(?:about|for|of)\s+([A-Za-z][A-Za-z .'-]{0,100})$",
        ]
    elif operation == "update":
        patterns = [
            (
                r"\b(?:update|udpate|updae|change|chnage|modify|set|edit)\s+"
                r"(?:the\s+)?(?:user\s+)?([A-Za-z][A-Za-z .'-]{0,100}?)"
                r"(?:['’]s|\s+(?:phone|number|city|name))\b"
            ),
            r"^([A-Za-z][A-Za-z .'-]{0,100}?)\s+(?:moved|relocated|lives|resides)\b",
        ]

    for pattern in patterns:
        match = re.search(pattern, normalized_message, re.I)
        if match:
            candidate = _clean_name(match.group(1))
            if candidate and candidate.lower() not in {
                "user",
                "a user",
                "new user",
                "her",
                "him",
                "his",
                "she",
                "he",
                "them",
                "that person",
            }:
                email = extract_email(normalized_message)
                if operation == "create" and email:
                    local_part = email.split("@", 1)[0].lower()
                    compact_candidate = candidate.lower().replace(" ", "")
                    has_explicit_email_label = bool(re.search(r"\bwith\s+email\b", normalized_message, re.I))
                    if not has_explicit_email_label and (
                        compact_candidate == local_part or "." in candidate
                    ):
                        continue
                return candidate
    return None


def _clean_city_value(value: str) -> str:
    cleaned = " ".join(value.strip(" ,.;:'\"!?").split())
    cleaned = re.sub(
        r"^(?:(?:should|must)\s+be|needs?\s+to\s+be)\s+",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(
        r"\s+(?:now|please|recently)$",
        "",
        cleaned,
        flags=re.I,
    )
    return cleaned.strip()


def _extract_city_semantic(message: str) -> str | None:
    # Prefer explicit city-update grammar before the generic parser so filler
    # such as "should be" never becomes part of the stored database value.
    patterns = [
        (
            r"\bcity\s*(?:(?:should|must)\s+be|needs?\s+to\s+be|"
            r"is|=|:|to)\s+([A-Za-z][A-Za-z .'-]{1,80}?)"
            r"(?:\s+(?:now|please|recently))?[.?!]*$"
        ),
        r"\b(?:moved|relocated)\s+to\s+([A-Za-z][A-Za-z .'-]{1,80})",
        r"\b(?:lives?|resides?)\s+in\s+([A-Za-z][A-Za-z .'-]{1,80})",
        r"\b(?:make\s+(?:it|that)|should\s+be)\s+([A-Za-z][A-Za-z .'-]{1,80})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.I)
        if match:
            city = _clean_city_value(match.group(1))
            if city:
                return city

    city = extract_city(message)
    if city:
        cleaned_city = _clean_city_value(city)
        return cleaned_city or None
    return None


def _extract_phone_semantic(message: str) -> str | None:
    phone = extract_phone(message)
    if phone:
        return phone
    if re.fullmatch(r"\s*\+?[0-9][0-9\s().-]{6,20}\s*", message):
        return " ".join(message.strip().split())
    match = re.search(r"\b(?:number|mobile|phone)\b.*?(\+?[0-9][0-9\s().-]{6,20})", message, re.I)
    return " ".join(match.group(1).strip().split()) if match else None


def _has_pronoun_reference(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:her|him|his|she|he|them|their|that\s+person|this\s+person|that\s+user)\b",
            text,
            re.I,
        )
    )


def _detect_explicit_operation(lowered: str) -> str:
    """Return a deterministic operation when the message states one clearly."""
    if _matches_any(CREATE_PATTERNS, lowered):
        return "create"
    if _matches_any(DELETE_PATTERNS, lowered):
        return "delete"
    if _matches_any(UPDATE_PATTERNS, lowered):
        return "update"
    if re.search(r"\b(?:how\s+many|count|total\s+(?:number\s+of\s+)?users?)\b", lowered):
        return "count"
    if re.search(r"\b(?:recent\s+)?(?:activity|audit\s+log|actions)\b", lowered):
        return "activity"
    if re.search(
        (
            r"\b(?:list\s+(?:me\s+)?(?:all\s+)?users?|"
            r"(?:show|display)\s+(?:me\s+)?all\s+users?|"
            r"(?:show|display)\s+users\s*$)"
        ),
        lowered,
    ):
        return "list"
    if _matches_any(READ_PATTERNS, lowered):
        return "read"
    return "none"


def fallback_interpret(
    message: str,
    conversation: Conversation,
) -> AssistantInterpretation:
    text = " ".join(message.strip().split())
    lowered = text.lower()
    fields = AssistantFields(
        email=extract_email(text),
        phone=_extract_phone_semantic(text),
        city=_extract_city_semantic(text),
    )
    user_id = extract_user_id(text)

    if _matches_any(CANCEL_PATTERNS, lowered):
        operation = conversation.current_intent or "none"
        if _matches_any(UPDATE_PATTERNS, lowered):
            return AssistantInterpretation(
                intent="switch_operation",
                operation="update",
                reference_type="current_user",
                fields=fields,
                control="cancel",
                confidence=0.92,
                explanation="Cancel the pending action and switch to updating the selected user.",
            )
        return AssistantInterpretation(
            intent="cancel",
            operation=operation if operation in {"create", "read", "update", "delete"} else "none",
            reference_type="current_user" if conversation.selected_user_id else "current_draft",
            control="cancel",
            confidence=0.96,
            explanation="The user wants to cancel the current workflow.",
        )

    if _matches_any(CONFIRM_PATTERNS, lowered):
        return AssistantInterpretation(
            intent="confirm",
            operation=conversation.current_intent or "none",
            reference_type="current_user",
            control="confirm",
            confidence=0.96,
            explanation="The user confirmed the pending action.",
        )

    if _matches_any(SKIP_PATTERNS, lowered):
        clean_control = lowered.strip(" .!?")

        wants_create_now = bool(
            re.fullmatch(
                r"create(?:\s+(?:her|him|them|it|the\s+user|this\s+user))?"
                r"\s+now",
                clean_control,
            )
        )

        requested_field = "none"

        if not wants_create_now:
            if clean_control in {"skip phone", "no phone"}:
                requested_field = "phone"
            elif clean_control in {"skip city", "no city"}:
                requested_field = "city"
            elif conversation.awaiting_field in {
                "name",
                "email",
                "phone",
                "city",
            }:
                requested_field = conversation.awaiting_field

        return AssistantInterpretation(
            intent="provide_information",
            operation=conversation.current_intent or "none",
            reference_type="current_draft",
            requested_field=requested_field,
            control="skip",
            confidence=0.99,
            explanation=(
                "The user wants to finish the current draft now."
                if wants_create_now
                else "The user wants to skip the current optional field."
            ),
        )

    if re.search(
        r"\b(?:who|which\s+user)\s+(?:were|are)\s+we\s+"
        r"(?:editing|talking\s+about|working\s+on)\b",
        lowered,
    ):
        return AssistantInterpretation(
            intent="ask_context",
            operation=conversation.current_intent or "none",
            reference_type="current_user",
            confidence=0.96,
            explanation="The user is asking for the current conversation context.",
        )

    if re.search(
        r"\b(?:what|which)\s+(?:information|details?|fields?)\s+"
        r"(?:is|are)\s+(?:still\s+)?missing\b",
        lowered,
    ):
        return AssistantInterpretation(
            intent="ask_context",
            operation=conversation.current_intent or "none",
            reference_type="current_draft",
            confidence=0.96,
            explanation="The user wants to know which information is still missing.",
        )

    if re.fullmatch(
        r"(?:hi|hello|hey|salam|assalamualaikum|"
        r"good\s+(?:morning|afternoon|evening))[!.\s]*",
        lowered,
    ):
        return AssistantInterpretation(
            intent="greeting",
            operation="none",
            confidence=0.99,
            explanation="A greeting.",
        )

    if re.search(r"\b(?:help|what\s+can\s+you\s+do|how\s+do\s+i\s+use)\b", lowered):
        return AssistantInterpretation(
            intent="help",
            operation="none",
            confidence=0.98,
            explanation="The user is asking for help.",
        )

    explicit_operation = _detect_explicit_operation(lowered)

    if (
        conversation.status == "awaiting_clarification"
        and explicit_operation == "none"
    ):
        ordinal = _extract_ordinal(text)
        if ordinal is not None or fields.email or user_id is not None:
            return AssistantInterpretation(
                intent="select_candidate",
                operation=conversation.current_intent or "read",
                reference_type="candidate",
                user_id=user_id,
                ordinal=ordinal,
                candidate_hint=None if ordinal is not None else text,
                fields=fields,
                confidence=0.93,
                explanation="The user is selecting one of the previously presented matches.",
            )
        return AssistantInterpretation(
            intent="select_candidate",
            operation=conversation.current_intent or "read",
            reference_type="candidate",
            candidate_hint=text,
            fields=fields,
            confidence=0.72,
            explanation="The message likely describes one of the presented candidates.",
        )

    if (
        conversation.status == "collecting_fields"
        and conversation.current_intent == "create"
    ):
        awaiting = conversation.awaiting_field
        supplied_requested_value = (
            (awaiting == "name" and bool(fields.name))
            or (awaiting == "email" and bool(fields.email))
            or (awaiting == "phone" and bool(fields.phone))
            or (awaiting == "city" and bool(fields.city))
        )
        if supplied_requested_value:
            return AssistantInterpretation(
                intent="provide_information",
                operation="create",
                reference_type="current_draft",
                requested_field=(
                    awaiting
                    if awaiting in {"name", "email", "phone", "city"}
                    else "none"
                ),
                fields=fields,
                confidence=0.96,
                explanation="The user supplied the field requested for the pending user draft.",
            )

    if explicit_operation != "none":
        reference_type = "none"
        if fields.email:
            reference_type = "email"
        elif user_id is not None:
            reference_type = "id"
        elif _has_pronoun_reference(lowered):
            reference_type = "current_user"

        name = _extract_name(text, explicit_operation)
        if name:
            fields.name = name
            if reference_type == "none" and explicit_operation != "create":
                reference_type = "name"

        intent = "start_operation"
        if conversation.current_intent and explicit_operation != conversation.current_intent:
            intent = "switch_operation"

        requested_field = "none"
        if explicit_operation == "update":
            if re.search(r"\b(?:phone|mobile|number)\b", lowered):
                requested_field = "phone"
            elif re.search(r"\bcity\b|\b(?:moved|relocated|lives|resides)\b", lowered):
                requested_field = "city"
            elif re.search(r"\bname\b", lowered):
                requested_field = "name"

        return AssistantInterpretation(
            intent=intent,
            operation=explicit_operation,
            reference_type=reference_type,
            user_id=user_id,
            requested_field=requested_field,
            fields=fields,
            control="continue",
            confidence=0.9,
            explanation=f"The user wants to {explicit_operation} user data.",
        )

    if conversation.status in {"collecting_fields", "awaiting_confirmation"}:
        if conversation.awaiting_field == "name" and not fields.name:
            fields.name = _clean_name(text)
        elif conversation.awaiting_field == "city" and not fields.city:
            fields.city = _clean_name(text)
        elif conversation.awaiting_field == "phone" and not fields.phone:
            fields.phone = _extract_phone_semantic(text)

        if any([fields.name, fields.email, fields.phone, fields.city]):
            return AssistantInterpretation(
                intent="provide_information",
                operation=conversation.current_intent or "none",
                reference_type=(
                    "current_draft" if conversation.current_intent == "create" else "current_user"
                ),
                requested_field=(
                    conversation.awaiting_field
                    if conversation.awaiting_field in {"name", "email", "phone", "city"}
                    else "none"
                ),
                fields=fields,
                confidence=0.94,
                explanation="The user supplied information requested by the active workflow.",
            )

    if conversation.selected_user_id and (
        _has_pronoun_reference(lowered)
        or re.search(r"\b(?:that|this)\s+(?:one|person|user)\b", lowered)
    ):
        if fields.city or fields.phone or fields.name:
            return AssistantInterpretation(
                intent="start_operation",
                operation="update",
                reference_type="current_user",
                fields=fields,
                confidence=0.86,
                explanation="The user is updating the currently selected user.",
            )
        return AssistantInterpretation(
            intent="start_operation",
            operation="read",
            reference_type="current_user",
            confidence=0.76,
            explanation="The user refers to the currently selected user.",
        )

    if fields.email and conversation.current_intent:
        return AssistantInterpretation(
            intent="provide_information",
            operation=conversation.current_intent,
            reference_type=(
                "current_draft" if conversation.current_intent == "create" else "current_user"
            ),
            fields=fields,
            confidence=0.91,
            explanation="The user supplied an email for the active workflow.",
        )

    if any([fields.name, fields.email, fields.phone, fields.city]):
        return AssistantInterpretation(
            intent="provide_information",
            operation="none",
            reference_type="none",
            fields=fields,
            confidence=0.7,
            explanation="The user supplied user information without an active operation.",
        )

    return AssistantInterpretation(
        intent="unknown",
        operation="none",
        fields=fields,
        confidence=0.15,
        explanation="The fallback interpreter could not determine a safe operation.",
    )


def _conversation_snapshot(conversation: Conversation) -> dict:
    return {
        "status": conversation.status,
        "current_intent": conversation.current_intent,
        "awaiting_field": conversation.awaiting_field,
        "selected_user_id": conversation.selected_user_id,
        "draft_fields": conversation.draft_fields or {},
        "candidate_user_ids": conversation.candidate_user_ids or [],
        "pending_action": conversation.pending_action,
    }


def _recent_message_payload(
    messages: list[ConversationMessage],
    limit: int,
) -> list[dict[str, str]]:
    """
    Convert recent saved messages into the format sent to the LLM.

    The configurable limit prevents extremely long conversations from
    increasing latency and token usage unnecessarily.
    """
    safe_limit = max(1, min(limit, 50))

    return [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in messages[-safe_limit:]
        if message.role in {"user", "assistant"}
        and message.content.strip()
    ]

def interpret_message(
    message: str,
    conversation: Conversation,
    recent_messages: list[ConversationMessage],
) -> tuple[AssistantInterpretation, str]:
    """
    Understand one user message.

    Processing order:
    1. Handle safety-critical control commands deterministically.
    2. Use the configured OpenAI-compatible AI provider when available.
    3. Validate the returned interpretation and confidence.
    4. Fall back safely when AI is disabled or unavailable.

    The model never performs database operations directly.
    It only returns a structured AssistantInterpretation.
    """
    current_settings = get_settings()

    # Control commands and context questions must behave deterministically
    # even when an AI provider is enabled. This keeps buttons such as
    # "Skip phone", "Create now", confirmations, cancellations, candidate
    # selections, and saved-context questions reliable.
    deterministic_interpretation = fallback_interpret(
        message,
        conversation,
    )

    has_concrete_reference = (
        deterministic_interpretation.reference_type
        in {"name", "email", "id", "current_user", "candidate"}
        or deterministic_interpretation.user_id is not None
        or bool(deterministic_interpretation.fields.name)
        or bool(deterministic_interpretation.fields.email)
    )

    # Prefer deterministic parsing whenever it has safely recognized both the
    # operation and a concrete target. This prevents an AI-provider response
    # from dropping an explicitly typed name such as "find lizzz".
    if (
        deterministic_interpretation.control
        in {"skip", "confirm", "cancel"}
        or deterministic_interpretation.intent
        in {
            "confirm",
            "cancel",
            "switch_operation",
            "select_candidate",
            "ask_context",
        }
        or deterministic_interpretation.operation in {"list", "count", "activity"}
        or (
            deterministic_interpretation.operation
            in {"read", "update", "delete"}
            and has_concrete_reference
        )
    ):
        return deterministic_interpretation, "fallback"

    if current_settings.ai_ready:
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=current_settings.openai_api_key,
                base_url=current_settings.openai_base_url,
                timeout=current_settings.openai_timeout_seconds,
                max_retries=1,
            )

            context_payload = {
                "conversation_state": _conversation_snapshot(
                    conversation,
                ),
                "recent_messages": _recent_message_payload(
                    recent_messages,
                    current_settings.assistant_context_message_limit,
                ),
                "current_user_message": message,
            }

            response = client.responses.parse(
                model=current_settings.openai_model,
                input=[
                    {
                        "role": "developer",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            context_payload,
                            ensure_ascii=False,
                        ),
                    },
                ],
                text_format=AssistantInterpretation,
                max_output_tokens=(
                    current_settings.openai_max_output_tokens
                ),
            )

            interpretation = response.output_parsed

            if interpretation is not None:
                if (
                    interpretation.confidence
                    < current_settings.assistant_min_confidence
                ):
                    return (
                        AssistantInterpretation(
                            intent="unknown",
                            operation="none",
                            reference_type="none",
                            fields=interpretation.fields,
                            control="none",
                            confidence=interpretation.confidence,
                            explanation=(
                                "The AI interpretation was below the "
                                "configured confidence threshold."
                            ),
                        ),
                        "openai",
                    )

                return interpretation, "openai"

            logger.warning(
                "AI provider returned no parsed assistant interpretation. "
                "Using deterministic fallback."
            )

        except Exception as error:
            # The chatbot must remain operational during:
            # - missing or invalid credentials
            # - network errors
            # - rate limits
            # - invalid model configuration
            # - structured-output validation errors
            #
            # Do not log the API key or complete user conversation.
            logger.warning(
                "AI-provider interpretation failed; using fallback: %s",
                error,
            )

    return (
        fallback_interpret(
            message,
            conversation,
        ),
        "fallback",
    )