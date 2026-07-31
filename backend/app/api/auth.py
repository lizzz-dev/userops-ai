from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_account
from app.core.config import get_settings
from app.db.database import get_db
from app.models.account import Account
from app.schemas.account import (
    AccountLogin,
    AccountResponse,
    AccountSignup,
    AuthResponse,
)
from app.services import account_service
from app.services.security import create_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    account_data: AccountSignup,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    try:
        account = account_service.create_account(db, account_data)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    set_session_cookie(response, create_access_token(account.id))
    return AuthResponse(
        message="Account created successfully.",
        account=AccountResponse.model_validate(account),
    )


@router.post("/login", response_model=AuthResponse)
def login(
    login_data: AccountLogin,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    account = account_service.authenticate_account(
        db,
        str(login_data.email),
        login_data.password,
    )
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    set_session_cookie(response, create_access_token(account.id))
    return AuthResponse(
        message="Login successful.",
        account=AccountResponse.model_validate(account),
    )


@router.get("/me", response_model=AccountResponse)
def me(
    account: Account = Depends(get_current_account),
) -> AccountResponse:
    return AccountResponse.model_validate(account)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
