from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_account
from app.db.database import get_db
from app.models.account import Account
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services import audit_service, user_service

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> UserResponse:
    try:
        user = user_service.create_user(db, account.id, user_data)
        audit_service.record_event(
            db,
            account_id=account.id,
            action="user_created",
            target_email=user.email,
            details={"id": user.id, "name": user.name},
        )
        return UserResponse.model_validate(user)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.get("", response_model=list[UserResponse])
def get_users(
    query: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> list[UserResponse]:
    users = user_service.get_users(
        db, account.id, query=query, limit=limit, offset=offset
    )
    return [UserResponse.model_validate(user) for user in users]


@router.get("/{email}", response_model=UserResponse)
def get_user(
    email: str,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> UserResponse:
    user = user_service.get_user_by_email(db, account.id, email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.patch("/{email}", response_model=UserResponse)
def update_user(
    email: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> UserResponse:
    user = user_service.update_user(db, account.id, email, user_data)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    audit_service.record_event(
        db,
        account_id=account.id,
        action="user_updated",
        target_email=user.email,
        details={"fields": user_data.model_dump(exclude_unset=True)},
    )
    return UserResponse.model_validate(user)


@router.delete("/{email}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    email: str,
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> None:
    deleted = user_service.delete_user(db, account.id, email)
    if deleted is None:
        raise HTTPException(status_code=404, detail="User not found")
    audit_service.record_event(
        db,
        account_id=account.id,
        action="user_deleted",
        target_email=deleted.email,
        details={"id": deleted.id, "name": deleted.name},
    )
