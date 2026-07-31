from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.user import User
from app.schemas.account import AccountSignup
from app.services.security import hash_password, verify_password


def get_account_by_email(db: Session, email: str) -> Account | None:
    statement = select(Account).where(Account.email == email.strip().lower())
    return db.scalar(statement)


def get_account_by_id(db: Session, account_id: int) -> Account | None:
    return db.get(Account, account_id)


def create_account(db: Session, account_data: AccountSignup) -> Account:
    account_count = int(db.scalar(select(func.count()).select_from(Account)) or 0)
    account = Account(
        full_name=account_data.full_name,
        email=str(account_data.email).lower(),
        password_hash=hash_password(account_data.password),
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ValueError("An account with this email already exists") from error

    db.refresh(account)

    # Preserve records from the earlier single-workspace prototype. Only the
    # first account can claim rows that do not yet belong to a workspace.
    if account_count == 0:
        db.execute(
            update(User)
            .where(User.owner_account_id.is_(None))
            .values(owner_account_id=account.id)
        )
        db.commit()

    return account


def authenticate_account(db: Session, email: str, password: str) -> Account | None:
    account = get_account_by_email(db, email)
    if account is None:
        return None
    if not verify_password(password, account.password_hash):
        return None
    return account
