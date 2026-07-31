from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_account
from app.core.config import get_settings
from app.db.database import get_db
from app.models.account import Account
from app.models.conversation_message import ConversationMessage
from app.schemas.chat import (
    ChatActionResponse,
    ChatRequest,
    ConfirmActionRequest,
)
from app.schemas.conversation import (
    ConversationHistoryResponse,
    ConversationListResponse,
    ConversationMessageResponse,
    ConversationRenameRequest,
    ConversationSummary,
)
from app.services import conversation_service
from app.services.assistant_interpreter import interpret_message
from app.services.dialogue_manager import (
    build_context,
    confirm_pending_delete,
    handle_interpretation,
)
from app.services.security import decode_delete_confirmation_token


router = APIRouter(prefix="/chat", tags=["Chat"])


def _response_metadata(response: ChatActionResponse) -> dict[str, Any]:
    """Build the metadata saved with an assistant message."""
    return {
        "status": response.status,
        "data": response.data,
        "action": (
            response.action.model_dump(mode="json")
            if response.action
            else None
        ),
        "suggestions": [
            suggestion.model_dump(mode="json")
            for suggestion in response.suggestions
        ],
        "context": (
            response.context.model_dump(mode="json")
            if response.context
            else None
        ),
        "interpretation": (
            response.interpretation.model_dump(mode="json")
            if response.interpretation
            else None
        ),
    }


def _infer_ai_mode(
    messages: list[ConversationMessage],
) -> str:
    """Restore the most recently saved interpreter mode."""
    for message in reversed(messages):
        metadata = message.message_metadata or {}
        context = metadata.get("context")

        if isinstance(context, dict):
            ai_mode = context.get("ai_mode")
            if ai_mode in {"openai", "fallback"}:
                return str(ai_mode)

    return "fallback"


def _serialize_messages(
    messages: list[ConversationMessage],
) -> list[ConversationMessageResponse]:
    """Convert saved database messages into the public response schema."""
    return [
        ConversationMessageResponse(
            id=message.id,
            role=message.role,
            content=message.content,
            metadata=message.message_metadata,
            created_at=message.created_at,
        )
        for message in messages
        if message.role in {"user", "assistant"}
    ]


@router.post("", response_model=ChatActionResponse)
def execute_chat_command(
    request: ChatRequest,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> ChatActionResponse:
    """Process one natural-language assistant message."""
    conversation = conversation_service.get_or_create_conversation(
        db,
        account.id,
        request.conversation_id,
    )

    current_settings = get_settings()

    recent_messages = conversation_service.get_recent_messages(
        db,
        conversation.id,
        limit=current_settings.assistant_context_message_limit,
    )

    conversation_service.add_message(
        db,
        conversation.id,
        "user",
        request.message,
    )

    interpretation, ai_mode = interpret_message(
        request.message,
        conversation,
        recent_messages,
    )

    response = handle_interpretation(
        db,
        account,
        conversation,
        interpretation,
        ai_mode,
        raw_message=request.message,
    )

    conversation_service.add_message(
        db,
        conversation.id,
        "assistant",
        response.reply,
        metadata=_response_metadata(response),
    )

    return response


@router.post("/confirm", response_model=ChatActionResponse)
def confirm_chat_action(
    request: ConfirmActionRequest,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> ChatActionResponse:
    """Confirm or cancel a pending deletion from the frontend action button."""
    token_data = decode_delete_confirmation_token(request.token)

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This confirmation has expired or is invalid. "
                "Please issue the delete command again."
            ),
        )

    token_account_id, email = token_data

    if token_account_id != account.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This confirmation does not belong to your account.",
        )

    if not request.conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A conversation ID is required to confirm a deletion.",
        )

    conversation = conversation_service.get_conversation(
        db,
        account.id,
        request.conversation_id,
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    previous_messages = conversation_service.get_all_messages(
        db,
        conversation.id,
    )
    ai_mode = _infer_ai_mode(previous_messages)

    pending = conversation.pending_action or {}

    if not pending:
        # Never recreate a deletion from an old signed token. The operator may
        # have cancelled it or switched to an update after the card was shown.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This deletion is no longer pending. Please issue a new delete "
                "command if you still want to remove the user."
            ),
        )

    if (
        pending.get("type") != "delete_user"
        or pending.get("email") != email
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The confirmation no longer matches the pending user.",
        )

    conversation_service.add_message(
        db,
        conversation.id,
        "user",
        "Confirm deletion" if request.confirm else "Cancel deletion",
    )

    response = confirm_pending_delete(
        db,
        account,
        conversation,
        ai_mode,
        confirmed=request.confirm,
    )

    conversation_service.add_message(
        db,
        conversation.id,
        "assistant",
        response.reply,
        metadata=_response_metadata(response),
    )

    return response


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> ConversationListResponse:
    """Return saved conversations owned by the logged-in account."""
    summaries = conversation_service.list_conversation_summaries(
        db,
        account.id,
        limit=50,
    )

    return ConversationListResponse(
        conversations=[
            ConversationSummary(**summary)
            for summary in summaries
        ]
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationSummary,
)
def rename_saved_conversation(
    conversation_id: str,
    request: ConversationRenameRequest,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> ConversationSummary:
    """Rename one saved conversation owned by the logged-in account."""
    conversation = conversation_service.get_conversation(
        db,
        account.id,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    cleaned_title = " ".join(request.title.strip().split())
    if not cleaned_title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conversation title cannot be empty.",
        )

    conversation_service.rename_conversation(
        db,
        conversation,
        cleaned_title,
    )

    summaries = conversation_service.list_conversation_summaries(
        db,
        account.id,
        limit=100,
    )
    renamed_summary = next(
        (
            summary
            for summary in summaries
            if summary["conversation_id"] == conversation_id
        ),
        None,
    )

    if renamed_summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation has no saved messages yet.",
        )

    return ConversationSummary(**renamed_summary)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
)
def get_conversation_history(
    conversation_id: str,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> ConversationHistoryResponse:
    """Restore one conversation owned by the logged-in account."""
    conversation = conversation_service.get_conversation(
        db,
        account.id,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    messages = conversation_service.get_all_messages(
        db,
        conversation.id,
    )
    ai_mode = _infer_ai_mode(messages)

    return ConversationHistoryResponse(
        conversation_id=conversation.id,
        context=build_context(
            db,
            account.id,
            conversation,
            ai_mode,
        ),
        messages=_serialize_messages(messages),
    )


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
)
def reset_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> ConversationHistoryResponse:
    """Clear workflow state, selected-user context, and saved chat history."""
    conversation = conversation_service.get_conversation(
        db,
        account.id,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    conversation_service.reset_conversation(
        db,
        conversation,
    )

    return ConversationHistoryResponse(
        conversation_id=conversation.id,
        context=build_context(
            db,
            account.id,
            conversation,
            "fallback",
        ),
        messages=[],
    )


@router.delete(
    "/conversations/{conversation_id}/permanent",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_saved_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> None:
    """Permanently delete one saved conversation owned by the account."""
    conversation = conversation_service.get_conversation(
        db,
        account.id,
        conversation_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    conversation_service.delete_conversation(db, conversation)
    return None