from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def create_user(
    db: Session,
    account_id: int,
    user_data: UserCreate,
) -> User:
    if get_user_by_email(db, account_id, str(user_data.email)):
        raise ValueError("A user with this email already exists in your workspace")

    user = User(
        owner_account_id=account_id,
        name=user_data.name,
        email=str(user_data.email).lower(),
        phone=user_data.phone,
        city=user_data.city,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ValueError("The user could not be created") from error

    db.refresh(user)
    return user


def get_users(
    db: Session,
    account_id: int,
    *,
    query: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[User]:
    statement = select(User).where(User.owner_account_id == account_id)
    if query:
        search_term = f"%{query.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(User.name).like(search_term),
                func.lower(User.email).like(search_term),
                func.lower(User.city).like(search_term),
            )
        )

    statement = (
        statement.order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())


def count_users(db: Session, account_id: int) -> int:
    statement = (
        select(func.count())
        .select_from(User)
        .where(User.owner_account_id == account_id)
    )
    return int(db.scalar(statement) or 0)


def get_user_by_email(
    db: Session,
    account_id: int,
    email: str,
) -> User | None:
    statement = select(User).where(
        User.owner_account_id == account_id,
        User.email == str(email).strip().lower(),
    )
    return db.scalar(statement)


def get_user_by_id(
    db: Session,
    account_id: int,
    user_id: int,
) -> User | None:
    statement = select(User).where(
        User.owner_account_id == account_id,
        User.id == user_id,
    )
    return db.scalar(statement)


def _normalize_name(value: str) -> str:
    """Return a case-insensitive, single-spaced name for safe comparisons."""
    return " ".join(value.strip().split()).casefold()


def get_users_by_name(
    db: Session,
    account_id: int,
    name: str,
) -> list[User]:
    """Resolve an exact name first, then a safe unique name-token match.

    This lets natural references such as ``Show Zara`` resolve ``Zara Khan``.
    It deliberately does not use fuzzy spelling or arbitrary substring matching:
    ``liz`` will not match ``Ali`` and duplicate first names still return multiple
    rows so the dialogue manager can ask the operator to clarify.
    """
    normalized_query = _normalize_name(name)
    if not normalized_query:
        return []

    exact_statement = select(User).where(
        User.owner_account_id == account_id,
        func.lower(User.name) == normalized_query,
    )
    exact_matches = list(db.scalars(exact_statement).all())
    if exact_matches:
        return exact_matches

    # Narrow the database result first, then enforce word-boundary semantics in
    # Python so this behaves consistently on both PostgreSQL and SQLite tests.
    candidate_statement = select(User).where(
        User.owner_account_id == account_id,
        User.name.is_not(None),
        func.lower(User.name).like(f"%{normalized_query}%"),
    )
    candidates = list(db.scalars(candidate_statement).all())
    query_parts = normalized_query.split()

    matches: list[User] = []
    for user in candidates:
        normalized_name = _normalize_name(user.name or "")
        name_parts = normalized_name.split()

        if len(query_parts) == 1:
            is_match = query_parts[0] in name_parts
        else:
            # Multi-word shortened references must match whole leading name
            # parts; arbitrary inner substrings are intentionally rejected.
            is_match = name_parts[: len(query_parts)] == query_parts

        if is_match:
            matches.append(user)

    return matches


def update_user(
    db: Session,
    account_id: int,
    email: str,
    user_data: UserUpdate,
) -> User | None:
    user = get_user_by_email(db, account_id, email)
    if user is None:
        return None

    update_data = user_data.model_dump(exclude_unset=True)
    if not update_data:
        return user

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(
    db: Session,
    account_id: int,
    email: str,
) -> User | None:
    user = get_user_by_email(db, account_id, email)
    if user is None:
        return None

    snapshot = User(
        id=user.id,
        owner_account_id=user.owner_account_id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        city=user.city,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
    db.delete(user)
    db.commit()
    return snapshot