from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.models.account import Account
from app.services import account_service
from app.services.security import decode_access_token

settings = get_settings()
session_cookie = APIKeyCookie(
    name=settings.session_cookie_name,
    auto_error=False,
)


def get_current_account(
    session_token: str | None = Depends(session_cookie),
    db: Session = Depends(get_db),
) -> Account:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    account_id = decode_access_token(session_token)
    if account_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    account = account_service.get_account_by_id(db, account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account no longer exists",
        )

    return account
