from typing import Literal, TypeAlias

from sqlalchemy.orm import Session

from app.models.user import User
from app.services import user_service


ResolutionStatus = Literal[
    "found",
    "not_found",
    "multiple_matches",
    "missing_reference",
]
ResolutionResult: TypeAlias = tuple[
    ResolutionStatus,
    User | list[User] | None,
]


def resolve_user(
    db: Session,
    account_id: int,
    *,
    email: str | None = None,
    name: str | None = None,
    user_id: int | None = None,
) -> ResolutionResult:
    if email:
        user = user_service.get_user_by_email(db, account_id, email)
        return ("found", user) if user else ("not_found", None)

    if user_id is not None:
        user = user_service.get_user_by_id(db, account_id, user_id)
        return ("found", user) if user else ("not_found", None)

    if name:
        users = user_service.get_users_by_name(db, account_id, name)
        if not users:
            return "not_found", None
        if len(users) > 1:
            return "multiple_matches", users
        return "found", users[0]

    return "missing_reference", None
