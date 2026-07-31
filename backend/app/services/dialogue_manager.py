import re

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.assistant import AssistantInterpretation
from app.schemas.chat import ChatAction, ChatActionResponse, ParsedCommand
from app.schemas.conversation import ConversationContext, ConversationSuggestion
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services import audit_service, conversation_service, user_service
from app.services.command_parser import extract_email
from app.services.security import create_delete_confirmation_token
from app.services.user_resolver import resolve_user

HELP_TEXT = (
    "I can create, find, update, list, count, and safely delete managed users. "
    "You can speak naturally and continue across messages. For example: “We have "
    "a new employee called Sara”, “Use sara@example.com for her”, or “Show Ali, "
    "then change his city to Karachi”."
)


_EMAIL_ADAPTER = TypeAdapter(EmailStr)


_BULK_DELETE_PATTERNS = (
    # Examples: "delete both", "remove all users", "delete both of them".
    r"\b(?:delete|remove|erase)\s+(?:both|all|every|multiple|several)\b",
    r"\b(?:delete|remove|erase)\b.*\b(?:both|all)\s+(?:of\s+)?"
    r"(?:them|these|those|users?|people|records?)\b",
    r"\b(?:delete|remove|erase)\b.*\b(?:them|these|those)\s+"
    r"(?:both|all)\b",
    r"\b(?:delete|remove|erase)\b.*\b(?:everyone|everybody)\b",
    r"\b(?:delete|remove|erase)\s+(?:the\s+)?"
    r"(?:two|three|four|five|\d+)\s+(?:users?|people|records?)\b",
)


def _requests_bulk_delete(message: str | None) -> bool:
    """Detect destructive requests that target more than one user.

    UserOps AI deliberately deletes one record at a time so every destructive
    action has an explicit target and its own confirmation step.
    """
    if not message or not message.strip():
        return False

    normalized = " ".join(message.lower().split())
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _BULK_DELETE_PATTERNS)


def _validated_email(value: object) -> str | None:
    """Return a normalized email or None without exposing Pydantic errors."""
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return str(_EMAIL_ADAPTER.validate_python(value.strip())).lower()
    except (ValidationError, TypeError, ValueError):
        return None


def _invalid_email_response(
    db: Session,
    account: Account,
    conversation: Conversation,
    interpretation: AssistantInterpretation,
    ai_mode: str,
) -> ChatActionResponse:
    """Keep the create draft active and ask for a corrected email."""
    draft = dict(conversation.draft_fields or {})
    draft.pop("email", None)
    conversation.draft_fields = draft
    conversation.status = "collecting_fields"
    conversation.current_intent = "create"
    conversation.awaiting_field = "email"
    conversation.selected_user_id = None

    return _response(
        db,
        account,
        conversation,
        ai_mode,
        status="invalid_field",
        reply=(
            "That email address is not valid. Please enter a complete address "
            "such as name@example.com."
        ),
        interpretation=interpretation,
    )


def serialize_user(user: User) -> dict:
    return UserResponse.model_validate(user).model_dump(mode="json")


def serialize_match(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "city": user.city,
    }


def parsed_from_interpretation(interpretation: AssistantInterpretation) -> ParsedCommand:
    operation = interpretation.operation
    intent = operation if operation in {
        "create",
        "read",
        "list",
        "count",
        "activity",
        "update",
        "delete",
    } else "unknown"
    fields = interpretation.fields.model_dump(exclude_none=True)
    email = fields.pop("email", None)
    name = fields.get("name")
    if operation != "create":
        fields.pop("name", None)
    return ParsedCommand(
        intent=intent,
        email=email,
        name=name,
        user_id=interpretation.user_id,
        fields={key: str(value) for key, value in fields.items()},
    )


def _selected_user(
    db: Session,
    account_id: int,
    conversation: Conversation,
) -> User | None:
    if conversation.selected_user_id is None:
        return None
    return user_service.get_user_by_id(
        db,
        account_id,
        conversation.selected_user_id,
    )


def build_context(
    db: Session,
    account_id: int,
    conversation: Conversation,
    ai_mode: str,
) -> ConversationContext:
    selected = _selected_user(db, account_id, conversation)
    pending_type = None
    if conversation.pending_action:
        pending_type = str(conversation.pending_action.get("type") or "") or None
    return ConversationContext(
        status=conversation.status,
        current_intent=conversation.current_intent,
        awaiting_field=conversation.awaiting_field,
        selected_user_id=conversation.selected_user_id,
        selected_user=serialize_match(selected) if selected else None,
        draft_fields=conversation.draft_fields or {},
        candidate_count=len(conversation.candidate_user_ids or []),
        pending_action=pending_type,
        ai_mode="openai" if ai_mode == "openai" else "fallback",
    )


def _response(
    db: Session,
    account: Account,
    conversation: Conversation,
    ai_mode: str,
    *,
    status: str,
    reply: str,
    interpretation: AssistantInterpretation | None = None,
    data: dict | list[dict] | None = None,
    action: ChatAction | None = None,
    suggestions: list[ConversationSuggestion] | None = None,
) -> ChatActionResponse:
    conversation_service.save_state(db, conversation)
    return ChatActionResponse(
        status=status,
        reply=reply,
        conversation_id=conversation.id,
        interpretation=interpretation,
        parsed=(
            parsed_from_interpretation(interpretation)
            if interpretation is not None
            else None
        ),
        data=data,
        action=action,
        suggestions=suggestions or [],
        context=build_context(db, account.id, conversation, ai_mode),
    )


def _merge_draft(
    conversation: Conversation,
    interpretation: AssistantInterpretation,
) -> dict:
    draft = dict(conversation.draft_fields or {})
    for field, value in interpretation.fields.model_dump(exclude_none=True).items():
        if isinstance(value, str) and value.strip():
            draft[field] = value.strip()
    conversation.draft_fields = draft
    return draft


def _create_user_from_draft(
    db: Session,
    account: Account,
    conversation: Conversation,
    interpretation: AssistantInterpretation,
    ai_mode: str,
) -> ChatActionResponse:
    draft = dict(conversation.draft_fields or {})
    email = draft.get("email")
    if not email:
        conversation.status = "collecting_fields"
        conversation.current_intent = "create"
        conversation.awaiting_field = "email"
        conversation.selected_user_id = None
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="collecting_fields",
            reply="What email address should I use for this user?",
            interpretation=interpretation,
        )

    normalized_email = _validated_email(email)
    if normalized_email is None:
        return _invalid_email_response(
            db,
            account,
            conversation,
            interpretation,
            ai_mode,
        )

    draft["email"] = normalized_email
    conversation.draft_fields = draft

    try:
        create_payload = UserCreate(
            name=draft.get("name"),
            email=normalized_email,
            phone=draft.get("phone"),
            city=draft.get("city"),
        )
        created_user = user_service.create_user(
            db,
            account.id,
            create_payload,
        )
    except ValidationError:
        # Never show raw Pydantic validation internals in the chat UI.
        return _invalid_email_response(
            db,
            account,
            conversation,
            interpretation,
            ai_mode,
        )
    except ValueError as error:
        existing = user_service.get_user_by_email(
            db,
            account.id,
            normalized_email,
        )
        conversation.selected_user_id = existing.id if existing else None
        conversation_service.clear_workflow(
            conversation,
            keep_selected_user=True,
            status="completed",
        )
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="error",
            reply=str(error),
            interpretation=interpretation,
            data=serialize_user(existing) if existing else None,
        )

    audit_service.record_event(
        db,
        account_id=account.id,
        action="user_created",
        target_email=created_user.email,
        details={"id": created_user.id, "name": created_user.name},
    )
    conversation.selected_user_id = created_user.id
    conversation_service.clear_workflow(
        conversation,
        keep_selected_user=True,
        status="completed",
    )
    return _response(
        db,
        account,
        conversation,
        ai_mode,
        status="success",
        reply=(
            f"Done — {created_user.name or created_user.email} was created "
            "successfully."
        ),
        interpretation=interpretation,
        data=serialize_user(created_user),
        suggestions=[
            ConversationSuggestion(
                label="Show this user",
                value="Show that person again",
            ),
            ConversationSuggestion(
                label="Add another user",
                value="I want to add another user",
                tone="primary",
            ),
        ],
    )


def _handle_create(
    db: Session,
    account: Account,
    conversation: Conversation,
    interpretation: AssistantInterpretation,
    ai_mode: str,
    *,
    was_collecting: bool,
    raw_message: str | None = None,
) -> ChatActionResponse:
    conversation.current_intent = "create"

    # A new create operation must not inherit an older selected user. This
    # prevents pronouns such as "her" from targeting an unrelated record if
    # the new draft has not been created yet.
    if not was_collecting:
        conversation.selected_user_id = None

    # Validate an email at the moment it is collected. The AI may classify a
    # value such as "zara.com" as an email, but it must never be accepted into
    # the draft or shown later as a raw Pydantic error.
    if was_collecting and conversation.awaiting_field == "email":
        interpreted_email = interpretation.fields.email
        message_email = extract_email(raw_message or "")
        normalized_email = _validated_email(message_email or interpreted_email)

        if normalized_email is None:
            return _invalid_email_response(
                db,
                account,
                conversation,
                interpretation,
                ai_mode,
            )

        draft = dict(conversation.draft_fields or {})
        draft["email"] = normalized_email

        for field, value in interpretation.fields.model_dump(
            exclude_none=True,
        ).items():
            if field == "email":
                continue
            if isinstance(value, str) and value.strip():
                draft[field] = value.strip()

        conversation.draft_fields = draft
    else:
        draft = _merge_draft(conversation, interpretation)

        supplied_email = draft.get("email")
        if supplied_email:
            normalized_email = _validated_email(supplied_email)
            if normalized_email is None:
                return _invalid_email_response(
                    db,
                    account,
                    conversation,
                    interpretation,
                    ai_mode,
                )
            draft["email"] = normalized_email
            conversation.draft_fields = draft

    if interpretation.control == "skip":
        if conversation.awaiting_field == "phone":
            conversation.status = "collecting_fields"
            conversation.awaiting_field = "city"
            return _response(
                db,
                account,
                conversation,
                ai_mode,
                status="collecting_fields",
                reply=(
                    "No problem. What city should I save? You can also say “skip” "
                    "or “create now”."
                ),
                interpretation=interpretation,
                suggestions=[
                    ConversationSuggestion(label="Skip city", value="Skip city"),
                    ConversationSuggestion(
                        label="Create now",
                        value="Create the user now",
                        tone="primary",
                    ),
                ],
            )
        return _create_user_from_draft(
            db,
            account,
            conversation,
            interpretation,
            ai_mode,
        )

    if not draft.get("name") and not draft.get("email"):
        conversation.status = "collecting_fields"
        conversation.awaiting_field = "name"
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="collecting_fields",
            reply="Sure. What is the new user's name?",
            interpretation=interpretation,
        )

    if not draft.get("email"):
        conversation.status = "collecting_fields"
        conversation.awaiting_field = "email"
        subject = draft.get("name") or "the new user"
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="collecting_fields",
            reply=f"What email address should I use for {subject}?",
            interpretation=interpretation,
        )

    # A complete one-message create command should stay fast. A multi-turn draft
    # offers optional phone/city collection before execution.
    if not was_collecting:
        return _create_user_from_draft(
            db,
            account,
            conversation,
            interpretation,
            ai_mode,
        )

    if not draft.get("phone") and conversation.awaiting_field in {"email", "phone", "name"}:
        conversation.status = "collecting_fields"
        conversation.awaiting_field = "phone"
        subject = draft.get("name") or draft.get("email")
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="collecting_fields",
            reply=(
                f"Got it. What is {subject}'s phone number? You can say “skip” "
                "or “create now”."
            ),
            interpretation=interpretation,
            suggestions=[
                ConversationSuggestion(label="Skip phone", value="Skip phone"),
                ConversationSuggestion(
                    label="Create now",
                    value="Create the user now",
                    tone="primary",
                ),
            ],
        )

    if not draft.get("city") and conversation.awaiting_field in {"phone", "city"}:
        conversation.status = "collecting_fields"
        conversation.awaiting_field = "city"
        subject = draft.get("name") or draft.get("email")
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="collecting_fields",
            reply=(
                f"Thanks. Which city should I save for {subject}? You can say "
                "“skip” or “create now”."
            ),
            interpretation=interpretation,
            suggestions=[
                ConversationSuggestion(label="Skip city", value="Skip city"),
                ConversationSuggestion(
                    label="Create now",
                    value="Create the user now",
                    tone="primary",
                ),
            ],
        )

    return _create_user_from_draft(
        db,
        account,
        conversation,
        interpretation,
        ai_mode,
    )


def _resolve_interpretation_target(
    db: Session,
    account: Account,
    conversation: Conversation,
    interpretation: AssistantInterpretation,
):
    fields = interpretation.fields
    email = fields.email if interpretation.reference_type == "email" else None
    name = fields.name if interpretation.reference_type == "name" else None
    user_id = interpretation.user_id if interpretation.reference_type == "id" else None

    if interpretation.reference_type == "current_user" and conversation.selected_user_id:
        user_id = conversation.selected_user_id

    if not any([email, name, user_id is not None]):
        if fields.email:
            email = fields.email
        elif interpretation.user_id is not None:
            user_id = interpretation.user_id
        elif fields.name and interpretation.operation != "create":
            name = fields.name
        elif conversation.selected_user_id:
            user_id = conversation.selected_user_id

    return resolve_user(
        db,
        account.id,
        email=email,
        name=name,
        user_id=user_id,
    )


def _candidate_users(
    db: Session,
    account: Account,
    conversation: Conversation,
) -> list[User]:
    candidates: list[User] = []
    for user_id in conversation.candidate_user_ids or []:
        user = user_service.get_user_by_id(db, account.id, int(user_id))
        if user:
            candidates.append(user)
    return candidates


def _select_candidate(
    db: Session,
    account: Account,
    conversation: Conversation,
    interpretation: AssistantInterpretation,
) -> User | None:
    candidates = _candidate_users(db, account, conversation)
    if not candidates:
        return None

    if interpretation.user_id is not None:
        return next((user for user in candidates if user.id == interpretation.user_id), None)

    if interpretation.fields.email:
        wanted = interpretation.fields.email.lower()
        return next((user for user in candidates if user.email.lower() == wanted), None)

    if interpretation.ordinal == -1 and len(candidates) == 2:
        if conversation.selected_user_id:
            return next(
                (user for user in candidates if user.id != conversation.selected_user_id),
                candidates[1],
            )
        return candidates[1]

    if interpretation.ordinal and interpretation.ordinal > 0:
        index = interpretation.ordinal - 1
        return candidates[index] if index < len(candidates) else None

    hint = (interpretation.candidate_hint or "").lower()
    if hint:
        matches = [
            user
            for user in candidates
            if any(
                value and str(value).lower() in hint
                for value in [user.email, user.city, user.name, user.id]
            )
        ]
        if len(matches) == 1:
            return matches[0]
    return None


def _ask_for_candidate(
    db: Session,
    account: Account,
    conversation: Conversation,
    interpretation: AssistantInterpretation,
    ai_mode: str,
    candidates: list[User],
) -> ChatActionResponse:
    conversation.status = "awaiting_clarification"
    conversation.candidate_user_ids = [user.id for user in candidates]
    choices = "\n".join(
        f"{index}. {user.name or 'Unnamed user'} — {user.email}"
        + (f" — {user.city}" if user.city else "")
        for index, user in enumerate(candidates, start=1)
    )
    suggestions = [
        ConversationSuggestion(
            label=f"{index}. {user.email}",
            value=f"The {index}{'st' if index == 1 else 'nd' if index == 2 else 'th'} one",
        )
        for index, user in enumerate(candidates[:4], start=1)
    ]
    return _response(
        db,
        account,
        conversation,
        ai_mode,
        status="needs_clarification",
        reply=(
            "I found multiple matching users. Which one do you mean?\n\n"
            f"{choices}"
        ),
        interpretation=interpretation,
        data=[serialize_match(user) for user in candidates],
        suggestions=suggestions,
    )


def _perform_read(
    db: Session,
    account: Account,
    conversation: Conversation,
    interpretation: AssistantInterpretation,
    ai_mode: str,
    user: User,
) -> ChatActionResponse:
    conversation.selected_user_id = user.id
    conversation_service.clear_workflow(
        conversation,
        keep_selected_user=True,
        status="completed",
    )
    return _response(
        db,
        account,
        conversation,
        ai_mode,
        status="success",
        reply=f"I found {user.name or user.email}.",
        interpretation=interpretation,
        data=serialize_user(user),
        suggestions=[
            ConversationSuggestion(
                label="Update this user",
                value="I want to update this user",
            ),
            ConversationSuggestion(
                label="Delete this user",
                value="Delete this user",
                tone="danger",
            ),
        ],
    )


def _clean_city_for_storage(value: str) -> str:
    """Defensive cleanup for city values returned by either parser or AI."""
    cleaned = " ".join(value.strip(" ,.;:'\"!?").split())
    cleaned = re.sub(
        r"^(?:(?:should|must)\s+be|needs?\s+to\s+be)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s+(?:now|please|recently)$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def _perform_update(
    db: Session,
    account: Account,
    conversation: Conversation,
    interpretation: AssistantInterpretation,
    ai_mode: str,
    user: User,
) -> ChatActionResponse:
    update_fields = interpretation.fields.model_dump(exclude_none=True)
    update_fields.pop("email", None)

    city_value = update_fields.get("city")
    if isinstance(city_value, str):
        cleaned_city = _clean_city_for_storage(city_value)
        if cleaned_city:
            update_fields["city"] = cleaned_city
        else:
            update_fields.pop("city", None)

    if not update_fields:
        conversation.status = "collecting_fields"
        conversation.current_intent = "update"
        conversation.selected_user_id = user.id
        requested_field = interpretation.requested_field
        if requested_field in {"name", "phone", "city"}:
            conversation.awaiting_field = requested_field
            question = (
                f"What should {user.name or user.email}'s new {requested_field} be?"
            )
        else:
            conversation.awaiting_field = "field_to_update"
            question = (
                f"What would you like to change for {user.name or user.email}: "
                "name, phone, or city?"
            )
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="collecting_fields",
            reply=question,
            interpretation=interpretation,
            data=serialize_user(user),
            suggestions=[
                ConversationSuggestion(label="Change city", value="Change the city"),
                ConversationSuggestion(label="Change phone", value="Change the phone number"),
                ConversationSuggestion(label="Change name", value="Change the name"),
            ],
        )

    updated = user_service.update_user(
        db,
        account.id,
        user.email,
        UserUpdate(**update_fields),
    )
    if updated is None:
        conversation_service.clear_workflow(conversation, keep_selected_user=False)
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="not_found",
            reply="That user no longer exists.",
            interpretation=interpretation,
        )

    audit_service.record_event(
        db,
        account_id=account.id,
        action="user_updated",
        target_email=updated.email,
        details={"fields": update_fields},
    )
    conversation.selected_user_id = updated.id
    conversation_service.clear_workflow(
        conversation,
        keep_selected_user=True,
        status="completed",
    )
    changed = ", ".join(update_fields)
    return _response(
        db,
        account,
        conversation,
        ai_mode,
        status="success",
        reply=(
            f"Done — I updated {changed} for {updated.name or updated.email}."
        ),
        interpretation=interpretation,
        data=serialize_user(updated),
    )


def _handle_bulk_delete_request(
    db: Session,
    account: Account,
    conversation: Conversation,
    interpretation: AssistantInterpretation,
    ai_mode: str,
) -> ChatActionResponse:
    """Reject bulk deletion and guide the operator to one safe target."""
    users = user_service.get_users(db, account.id, limit=8)

    # A plural delete request must never inherit an older selected user or a
    # stale confirmation card. Start a fresh, non-destructive selection flow.
    conversation_service.clear_workflow(
        conversation,
        keep_selected_user=False,
        status="idle",
    )

    if not users:
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="success",
            reply="There are no managed users to delete.",
            interpretation=interpretation,
            data=[],
        )

    conversation.status = "awaiting_clarification"
    conversation.current_intent = "delete"
    conversation.awaiting_field = "user_reference"
    conversation.candidate_user_ids = [user.id for user in users]

    choices = "\n".join(
        f"{index}. {user.name or 'Unnamed user'} — {user.email} (ID {user.id})"
        for index, user in enumerate(users, start=1)
    )

    suggestions = [
        ConversationSuggestion(
            label=f"Delete {user.name or user.email}",
            value=f"Delete the user with email {user.email}",
            tone="danger",
        )
        for user in users[:4]
    ]

    return _response(
        db,
        account,
        conversation,
        ai_mode,
        status="needs_clarification",
        reply=(
            "For safety, bulk deletion is not supported. I can delete only "
            "one user at a time, and each deletion requires confirmation. "
            "Which single user should I delete?\n\n"
            f"{choices}"
        ),
        interpretation=interpretation,
        data=[serialize_match(user) for user in users],
        suggestions=suggestions,
    )


def _request_delete(
    db: Session,
    account: Account,
    conversation: Conversation,
    interpretation: AssistantInterpretation,
    ai_mode: str,
    user: User,
) -> ChatActionResponse:
    conversation.status = "awaiting_confirmation"
    conversation.current_intent = "delete"
    conversation.awaiting_field = None
    conversation.selected_user_id = user.id
    conversation.candidate_user_ids = []
    conversation.pending_action = {
        "type": "delete_user",
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
    }
    token = create_delete_confirmation_token(
        account_id=account.id,
        email=user.email,
    )
    return _response(
        db,
        account,
        conversation,
        ai_mode,
        status="needs_confirmation",
        reply=(
            f"{user.name or user.email} ({user.email}) will be permanently deleted. "
            "Should I continue?"
        ),
        interpretation=interpretation,
        data=serialize_user(user),
        action=ChatAction(
            type="confirm_delete",
            token=token,
            label="Confirm deletion",
        ),
        suggestions=[
            ConversationSuggestion(
                label="Confirm deletion",
                value="Yes, delete this user",
                tone="danger",
            ),
            ConversationSuggestion(label="Cancel", value="Actually don't delete this user"),
        ],
    )


def confirm_pending_delete(
    db: Session,
    account: Account,
    conversation: Conversation,
    ai_mode: str,
    *,
    confirmed: bool,
    interpretation: AssistantInterpretation | None = None,
) -> ChatActionResponse:
    pending = conversation.pending_action or {}
    if pending.get("type") != "delete_user":
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="invalid",
            reply="There is no deletion waiting for confirmation.",
            interpretation=interpretation,
        )

    if not confirmed:
        user = _selected_user(db, account.id, conversation)
        conversation_service.clear_workflow(
            conversation,
            keep_selected_user=True,
            status="cancelled",
        )
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="cancelled",
            reply=(
                f"Deletion cancelled. {user.name or user.email} was not changed."
                if user
                else "Deletion cancelled. No record was changed."
            ),
            interpretation=interpretation,
        )

    email = str(pending.get("email") or "")
    user = user_service.get_user_by_email(db, account.id, email)
    if user is None:
        conversation_service.clear_workflow(conversation, keep_selected_user=False)
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="not_found",
            reply="That user has already been removed or no longer exists.",
            interpretation=interpretation,
        )

    deleted_data = serialize_user(user)
    display_name = user.name or user.email
    user_service.delete_user(db, account.id, email)
    audit_service.record_event(
        db,
        account_id=account.id,
        action="user_deleted",
        target_email=email,
        details={"id": deleted_data.get("id"), "name": deleted_data.get("name")},
    )
    conversation_service.clear_workflow(
        conversation,
        keep_selected_user=False,
        status="completed",
    )
    return _response(
        db,
        account,
        conversation,
        ai_mode,
        status="success",
        reply=f"Done — {display_name} was deleted successfully.",
        interpretation=interpretation,
        data=deleted_data,
    )


def handle_interpretation(
    db: Session,
    account: Account,
    conversation: Conversation,
    interpretation: AssistantInterpretation,
    ai_mode: str,
    raw_message: str | None = None,
) -> ChatActionResponse:
    was_collecting_create = (
        conversation.status == "collecting_fields"
        and conversation.current_intent == "create"
    )

    # Do not let "delete her" or "update him" jump from an unfinished create
    # draft to an older selected database user. An explicit name/email/ID may
    # still switch operations normally.
    if (
        was_collecting_create
        and conversation.draft_fields
        and interpretation.intent == "switch_operation"
        and interpretation.operation in {"read", "update", "delete"}
        and interpretation.reference_type in {"current_user", "current_draft"}
    ):
        draft_name = (conversation.draft_fields or {}).get("name") or "This user"
        missing = conversation.awaiting_field or "required information"
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="collecting_fields",
            reply=(
                f"{draft_name} has not been created yet. I still need a valid "
                f"{missing}. Please provide it, or say ‘cancel’ to discard this draft."
            ),
            interpretation=interpretation,
        )

    if interpretation.intent == "greeting":
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="success",
            reply="Hello! What would you like to do with your user directory?",
            interpretation=interpretation,
            suggestions=[
                ConversationSuggestion(label="Add a user", value="I want to add a new user"),
                ConversationSuggestion(label="List users", value="List all users"),
            ],
        )

    if interpretation.intent == "help":
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="success",
            reply=HELP_TEXT,
            interpretation=interpretation,
        )

    if interpretation.intent == "ask_context":
        selected = _selected_user(db, account.id, conversation)
        if conversation.current_intent == "create" and conversation.draft_fields:
            missing = conversation.awaiting_field or "nothing required"
            return _response(
                db,
                account,
                conversation,
                ai_mode,
                status="success",
                reply=(
                    f"We are creating a user. Current draft: {conversation.draft_fields}. "
                    f"I am waiting for: {missing}."
                ),
                interpretation=interpretation,
            )
        if selected:
            return _response(
                db,
                account,
                conversation,
                ai_mode,
                status="success",
                reply=f"We are currently talking about {selected.name or selected.email}.",
                interpretation=interpretation,
                data=serialize_user(selected),
            )
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="success",
            reply="There is no selected user or unfinished operation in this conversation.",
            interpretation=interpretation,
        )

    if interpretation.intent == "cancel":
        if conversation.pending_action:
            return confirm_pending_delete(
                db,
                account,
                conversation,
                ai_mode,
                confirmed=False,
                interpretation=interpretation,
            )

        has_unfinished_workflow = bool(
            conversation.current_intent
            or conversation.awaiting_field
            or conversation.draft_fields
            or conversation.candidate_user_ids
            or conversation.status
            in {
                "collecting_fields",
                "awaiting_clarification",
                "awaiting_confirmation",
            }
        )

        if has_unfinished_workflow:
            conversation_service.clear_workflow(
                conversation,
                keep_selected_user=True,
                status="cancelled",
            )
            return _response(
                db,
                account,
                conversation,
                ai_mode,
                status="cancelled",
                reply="Okay, I cancelled the unfinished operation. No record was changed.",
                interpretation=interpretation,
            )

        selected = _selected_user(db, account.id, conversation)
        if selected:
            return _response(
                db,
                account,
                conversation,
                ai_mode,
                status="success",
                reply=(
                    "There is no pending deletion to cancel. "
                    f"{selected.name or selected.email} has not been deleted."
                ),
                interpretation=interpretation,
                data=serialize_user(selected),
            )

        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="invalid",
            reply=(
                "There is no pending operation to cancel. If a deletion was already "
                "confirmed, it has already been completed and cannot be undone."
            ),
            interpretation=interpretation,
        )

    if interpretation.intent == "confirm":
        return confirm_pending_delete(
            db,
            account,
            conversation,
            ai_mode,
            confirmed=True,
            interpretation=interpretation,
        )

    if _requests_bulk_delete(raw_message):
        return _handle_bulk_delete_request(
            db,
            account,
            conversation,
            interpretation,
            ai_mode,
        )

    if interpretation.intent == "switch_operation":
        # A new explicit operation safely replaces any unfinished workflow,
        # including a deletion that was waiting for confirmation.
        conversation_service.clear_workflow(
            conversation,
            keep_selected_user=True,
            status="idle",
        )

    elif (
        interpretation.intent == "start_operation"
        and conversation.status in {
            "awaiting_clarification",
            "awaiting_confirmation",
        }
    ):
        # A fresh command such as "Where is Liz?" must not be treated as an
        # answer to an older duplicate-name question or stale delete card.
        conversation_service.clear_workflow(
            conversation,
            keep_selected_user=True,
            status="idle",
        )

    if interpretation.intent == "select_candidate":
        selected = _select_candidate(db, account, conversation, interpretation)
        if selected is None:
            return _response(
                db,
                account,
                conversation,
                ai_mode,
                status="needs_clarification",
                reply=(
                    "I could not safely tell which result you meant. Please use its "
                    "number, email, ID, or city."
                ),
                interpretation=interpretation,
                data=[
                    serialize_match(user)
                    for user in _candidate_users(db, account, conversation)
                ],
            )
        conversation.selected_user_id = selected.id
        conversation.candidate_user_ids = []
        operation = conversation.current_intent or interpretation.operation
        if operation == "delete":
            return _request_delete(
                db, account, conversation, interpretation, ai_mode, selected
            )
        if operation == "update":
            return _perform_update(
                db, account, conversation, interpretation, ai_mode, selected
            )
        return _perform_read(
            db, account, conversation, interpretation, ai_mode, selected
        )

    operation = interpretation.operation
    if operation == "none" and conversation.current_intent:
        operation = conversation.current_intent

    if operation == "create":
        return _handle_create(
            db,
            account,
            conversation,
            interpretation,
            ai_mode,
            was_collecting=was_collecting_create,
            raw_message=raw_message,
        )

    if operation == "list":
        users = user_service.get_users(db, account.id, limit=50)
        conversation_service.clear_workflow(conversation, keep_selected_user=True)
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="success",
            reply=(
                f"I found {len(users)} managed user(s)."
                if users
                else "There are no managed users yet."
            ),
            interpretation=interpretation,
            data=[serialize_user(user) for user in users],
        )

    if operation == "count":
        total = user_service.count_users(db, account.id)
        conversation_service.clear_workflow(conversation, keep_selected_user=True)
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="success",
            reply=f"There are {total} managed user(s) in this workspace.",
            interpretation=interpretation,
            data={"count": total},
        )

    if operation == "activity":
        events = audit_service.get_recent_events(db, account.id, limit=20)
        conversation_service.clear_workflow(conversation, keep_selected_user=True)
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="success",
            reply=(
                f"Here are the {len(events)} most recent workspace action(s)."
                if events
                else "No user-management activity has been recorded yet."
            ),
            interpretation=interpretation,
            data=[audit_service.serialize_event(event) for event in events],
        )

    if operation in {"read", "update", "delete"}:
        conversation.current_intent = operation

        # While updating a selected user, follow-up fields do not need a fresh reference.
        if operation == "update" and conversation.selected_user_id:
            update_values = interpretation.fields.model_dump(exclude_none=True)
            target_values = {
                "email": interpretation.fields.email,
                "name": interpretation.fields.name,
                "user_id": interpretation.user_id,
            }
            explicit_target = (
                interpretation.reference_type in {"email", "name", "id"}
                and any(target_values.values())
            )
            if update_values and not explicit_target:
                selected = _selected_user(db, account.id, conversation)
                if selected:
                    return _perform_update(
                        db,
                        account,
                        conversation,
                        interpretation,
                        ai_mode,
                        selected,
                    )

        resolution_status, result = _resolve_interpretation_target(
            db,
            account,
            conversation,
            interpretation,
        )
        if resolution_status == "missing_reference":
            conversation.status = "collecting_fields"
            conversation.awaiting_field = "user_reference"
            return _response(
                db,
                account,
                conversation,
                ai_mode,
                status="collecting_fields",
                reply="Which user do you mean? Please give me a name, email, or ID.",
                interpretation=interpretation,
            )
        if resolution_status == "not_found":
            return _response(
                db,
                account,
                conversation,
                ai_mode,
                status="not_found",
                reply="I could not find a user matching that reference.",
                interpretation=interpretation,
            )
        if resolution_status == "multiple_matches":
            assert isinstance(result, list)
            return _ask_for_candidate(
                db,
                account,
                conversation,
                interpretation,
                ai_mode,
                result,
            )

        assert isinstance(result, User)
        if operation == "read":
            return _perform_read(
                db, account, conversation, interpretation, ai_mode, result
            )
        if operation == "update":
            return _perform_update(
                db, account, conversation, interpretation, ai_mode, result
            )
        return _request_delete(
            db, account, conversation, interpretation, ai_mode, result
        )

    if interpretation.intent == "provide_information" and operation == "none":
        supplied = interpretation.fields.model_dump(exclude_none=True)
        field_names = ", ".join(supplied) or "information"
        return _response(
            db,
            account,
            conversation,
            ai_mode,
            status="collecting_fields",
            reply=(
                f"I have the {field_names}, but there is no active user operation. "
                "Whose information is this, and do you want to create or update the user?"
            ),
            interpretation=interpretation,
            suggestions=[
                ConversationSuggestion(
                    label="Create a user",
                    value="Use this information to create a new user",
                    tone="primary",
                ),
                ConversationSuggestion(
                    label="Update a user",
                    value="Use this information to update a user",
                ),
            ],
        )

    return _response(
        db,
        account,
        conversation,
        ai_mode,
        status="invalid",
        reply=(
            "I am not sure what you want me to do yet. You can speak naturally, "
            "but please tell me whether you want to add, find, update, list, count, "
            "or delete a user."
        ),
        interpretation=interpretation,
        suggestions=[
            ConversationSuggestion(label="What can you do?", value="What can you do?"),
            ConversationSuggestion(label="List users", value="List all users"),
        ],
    )