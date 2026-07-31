import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# These environment variables must be set before importing the application.
# The application settings and database engine are created during imports.
TEST_DB = Path(__file__).parent / "test_userops.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough"
os.environ["ENVIRONMENT"] = "test"
os.environ["COOKIE_SECURE"] = "false"
os.environ["COOKIE_SAMESITE"] = "lax"
os.environ["ALLOWED_ORIGINS"] = "http://testserver"

# Automated tests must never contact the real OpenAI API.
os.environ["AI_ENABLED"] = "false"
os.environ["OPENAI_API_KEY"] = ""
os.environ["ASSISTANT_CONTEXT_MESSAGE_LIMIT"] = "12"
os.environ["ASSISTANT_MIN_CONFIDENCE"] = "0.55"


from app.db.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    """
    Give every test a completely clean database.

    This prevents users, conversations, messages, and audit records from
    leaking from one test into another.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Unauthenticated API client.
    """
    with TestClient(app) as test_client:
        yield test_client


def signup_account(
    client: TestClient,
    *,
    full_name: str,
    email: str,
    password: str = "strong-password-123",
) -> None:
    """
    Create an operator account and leave the client authenticated through
    the session cookie returned by the signup endpoint.
    """
    response = client.post(
        "/auth/signup",
        json={
            "full_name": full_name,
            "email": email,
            "password": password,
            "password_confirm": password,
        },
    )

    assert response.status_code == 201, response.text


@pytest.fixture
def authenticated_client(
    client: TestClient,
) -> TestClient:
    """
    Client authenticated as the primary test operator.
    """
    signup_account(
        client,
        full_name="Test Admin",
        email="admin@example.com",
    )

    return client


@pytest.fixture
def second_authenticated_client() -> Generator[TestClient, None, None]:
    """
    A separately authenticated operator used for account-isolation tests.

    It has its own cookie jar and must not be able to access the primary
    operator's users or conversations.
    """
    with TestClient(app) as test_client:
        signup_account(
            test_client,
            full_name="Second Admin",
            email="second.admin@example.com",
        )

        yield test_client