from typing import Any, Literal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.conversation_message import ConversationMessage


MessageRole = Literal["user", "assistant", "system"]


def _commit(db: Session) -> None:
    """
    Commit the current transaction safely.

    If PostgreSQL rejects the transaction, rollback keeps
    the SQLAlchemy session usable for later requests.
    """
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _shorten_text(value: str, limit: int) -> str:
    """Return clean single-line text suitable for sidebar labels."""
    cleaned = " ".join(value.strip().split())

    if len(cleaned) <= limit:
        return cleaned

    return f"{cleaned[: limit - 1].rstrip()}…"


def get_conversation(
    db: Session,
    account_id: int,
    conversation_id: str,
) -> Conversation | None:
    """
    Return a conversation only when it belongs to the logged-in account.

    This prevents one operator from accessing another operator's
    conversation by guessing or copying its ID.
    """
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.account_id == account_id,
    )
    return db.scalar(statement)


def get_or_create_conversation(
    db: Session,
    account_id: int,
    conversation_id: str | None,
) -> Conversation:
    """
    Restore the requested owned conversation or create a fresh one.

    An invalid or foreign conversation ID is never exposed.
    Instead, a new conversation is created for the current account.
    """
    if conversation_id:
        existing_conversation = get_conversation(
            db,
            account_id,
            conversation_id,
        )
        if existing_conversation is not None:
            return existing_conversation

    conversation = Conversation(account_id=account_id)
    db.add(conversation)
    _commit(db)
    db.refresh(conversation)

    return conversation


def add_message(
    db: Session,
    conversation_id: str,
    role: MessageRole,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> ConversationMessage:
    """
    Save one user, assistant, or system message.

    Empty messages are rejected so conversation history remains clean.
    """
    cleaned_content = content.strip()

    if not cleaned_content:
        raise ValueError("Conversation message content cannot be empty.")

    if role not in {"user", "assistant", "system"}:
        raise ValueError(
            "Conversation message role must be user, assistant, or system."
        )

    message = ConversationMessage(
        conversation_id=conversation_id,
        role=role,
        content=cleaned_content,
        message_metadata=metadata,
    )

    db.add(message)
    _commit(db)
    db.refresh(message)

    return message


def get_recent_messages(
    db: Session,
    conversation_id: str,
    limit: int = 12,
) -> list[ConversationMessage]:
    """
    Return recent messages in normal chronological order.

    PostgreSQL first retrieves the newest messages efficiently,
    then Python reverses them before they are sent to the AI.
    """
    safe_limit = max(1, min(limit, 50))

    statement = (
        select(ConversationMessage)
        .where(
            ConversationMessage.conversation_id == conversation_id,
        )
        .order_by(ConversationMessage.id.desc())
        .limit(safe_limit)
    )

    messages = list(db.scalars(statement).all())
    messages.reverse()

    return messages


def get_all_messages(
    db: Session,
    conversation_id: str,
) -> list[ConversationMessage]:
    """Return the complete conversation history in chronological order."""
    statement = (
        select(ConversationMessage)
        .where(
            ConversationMessage.conversation_id == conversation_id,
        )
        .order_by(ConversationMessage.id.asc())
    )

    return list(db.scalars(statement).all())


def list_conversation_summaries(
    db: Session,
    account_id: int,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Return saved conversations for one account, newest activity first.

    The first user message becomes the title. Empty conversations are not
    listed, so clicking "New conversation" does not create blank sidebar rows.
    """
    safe_limit = max(1, min(limit, 100))

    conversations = list(
        db.scalars(
            select(Conversation).where(
                Conversation.account_id == account_id,
            )
        ).all()
    )

    summaries: list[dict[str, Any]] = []

    for conversation in conversations:
        visible_roles = ("user", "assistant")

        first_user_message = db.scalar(
            select(ConversationMessage)
            .where(
                ConversationMessage.conversation_id == conversation.id,
                ConversationMessage.role == "user",
            )
            .order_by(ConversationMessage.id.asc())
            .limit(1)
        )

        if first_user_message is None:
            continue

        latest_message = db.scalar(
            select(ConversationMessage)
            .where(
                ConversationMessage.conversation_id == conversation.id,
                ConversationMessage.role.in_(visible_roles),
            )
            .order_by(ConversationMessage.id.desc())
            .limit(1)
        )

        message_count = db.scalar(
            select(func.count(ConversationMessage.id)).where(
                ConversationMessage.conversation_id == conversation.id,
                ConversationMessage.role.in_(visible_roles),
            )
        )

        latest_message = latest_message or first_user_message

        title_message = db.scalar(
            select(ConversationMessage)
            .where(
                ConversationMessage.conversation_id == conversation.id,
                ConversationMessage.role == "system",
            )
            .order_by(ConversationMessage.id.desc())
        )

        custom_title: str | None = None
        if title_message is not None:
            metadata = title_message.message_metadata or {}
            if metadata.get("type") == "conversation_title":
                saved_title = metadata.get("title")
                if isinstance(saved_title, str) and saved_title.strip():
                    custom_title = saved_title.strip()

        summaries.append(
            {
                "conversation_id": conversation.id,
                "title": _shorten_text(
                    custom_title or first_user_message.content,
                    58,
                ),
                "preview": _shorten_text(latest_message.content, 96),
                "message_count": int(message_count or 0),
                "created_at": first_user_message.created_at,
                "updated_at": latest_message.created_at,
            }
        )

    summaries.sort(
        key=lambda item: item["updated_at"],
        reverse=True,
    )

    return summaries[:safe_limit]


def save_state(
    db: Session,
    conversation: Conversation,
) -> Conversation:
    """Persist the assistant's current workflow and context."""
    db.add(conversation)
    _commit(db)
    db.refresh(conversation)

    return conversation


def clear_workflow(
    conversation: Conversation,
    *,
    keep_selected_user: bool = True,
    status: str = "idle",
) -> None:
    """
    Clear temporary workflow data.

    The selected user may be preserved so follow-up messages such as
    'change her city' can still refer to the previously shown user.
    """
    selected_user_id = (
        conversation.selected_user_id
        if keep_selected_user
        else None
    )

    conversation.status = status
    conversation.current_intent = None
    conversation.awaiting_field = None
    conversation.draft_fields = {}
    conversation.candidate_user_ids = []
    conversation.pending_action = None
    conversation.selected_user_id = selected_user_id


def reset_conversation(
    db: Session,
    conversation: Conversation,
) -> Conversation:
    """
    Completely reset one conversation.

    This clears:
    - active workflow state
    - selected user context
    - draft information
    - duplicate candidates
    - pending actions
    - previous message history
    """
    clear_workflow(
        conversation,
        keep_selected_user=False,
        status="idle",
    )

    db.execute(
        delete(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation.id,
        )
    )

    db.add(conversation)
    _commit(db)
    db.refresh(conversation)

    return conversation



def rename_conversation(
    db: Session,
    conversation: Conversation,
    title: str,
) -> None:
    """Save a custom sidebar title without changing visible chat messages."""
    cleaned_title = " ".join(title.strip().split())

    if not cleaned_title:
        raise ValueError("Conversation title cannot be empty.")

    existing_title_message = db.scalar(
        select(ConversationMessage)
        .where(
            ConversationMessage.conversation_id == conversation.id,
            ConversationMessage.role == "system",
        )
        .order_by(ConversationMessage.id.desc())
    )

    metadata = {
        "type": "conversation_title",
        "title": cleaned_title,
    }

    if existing_title_message is not None and (
        existing_title_message.message_metadata or {}
    ).get("type") == "conversation_title":
        existing_title_message.content = f"Conversation renamed to: {cleaned_title}"
        existing_title_message.message_metadata = metadata
        db.add(existing_title_message)
    else:
        db.add(
            ConversationMessage(
                conversation_id=conversation.id,
                role="system",
                content=f"Conversation renamed to: {cleaned_title}",
                message_metadata=metadata,
            )
        )

    _commit(db)

def delete_conversation(
    db: Session,
    conversation: Conversation,
) -> None:
    """Permanently delete one conversation and all of its messages."""
    db.execute(
        delete(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation.id,
        )
    )
    db.delete(conversation)
    _commit(db)