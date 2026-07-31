from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    app_name: str = "UserOps AI API"
    environment: str = "development"

    # Database and authentication
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60 * 24
    delete_token_expire_minutes: int = 5

    # Authentication cookie
    session_cookie_name: str = "userops_session"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # Frontend origins
    allowed_origins: str = (
        "http://localhost:3001,"
        "http://127.0.0.1:3001"
    )

    # Conversational AI
    #
    # OPENAI_* names are kept because the project uses the
    # OpenAI-compatible Python client. The provider may be Groq.
    ai_enabled: bool = False
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.groq.com/openai/v1"
    openai_model: str = "openai/gpt-oss-20b"
    openai_timeout_seconds: float = 20.0
    openai_max_output_tokens: int = 1200

    # Conversation understanding
    assistant_context_message_limit: int = 12
    assistant_min_confidence: float = 0.55

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cookie_samesite")
    @classmethod
    def validate_cookie_samesite(cls, value: str) -> str:
        normalized = value.strip().lower()

        if normalized not in {"lax", "strict", "none"}:
            raise ValueError(
                "COOKIE_SAMESITE must be lax, strict, or none"
            )

        return normalized

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def normalize_openai_api_key(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        return normalized or None

    @field_validator("openai_base_url")
    @classmethod
    def normalize_openai_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")

        if not normalized.startswith(("http://", "https://")):
            raise ValueError(
                "OPENAI_BASE_URL must start with http:// or https://"
            )

        return normalized

    @field_validator("openai_model")
    @classmethod
    def validate_openai_model(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("OPENAI_MODEL cannot be empty")

        return normalized

    @field_validator("openai_timeout_seconds")
    @classmethod
    def validate_openai_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError(
                "OPENAI_TIMEOUT_SECONDS must be greater than 0"
            )

        return value

    @field_validator("openai_max_output_tokens")
    @classmethod
    def validate_max_output_tokens(cls, value: int) -> int:
        if value < 100 or value > 5000:
            raise ValueError(
                "OPENAI_MAX_OUTPUT_TOKENS must be between 100 and 5000"
            )

        return value

    @field_validator("assistant_context_message_limit")
    @classmethod
    def validate_context_message_limit(cls, value: int) -> int:
        if value < 1 or value > 50:
            raise ValueError(
                "ASSISTANT_CONTEXT_MESSAGE_LIMIT must be between 1 and 50"
            )

        return value

    @field_validator("assistant_min_confidence")
    @classmethod
    def validate_min_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError(
                "ASSISTANT_MIN_CONFIDENCE must be between 0 and 1"
            )

        return value

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def ai_ready(self) -> bool:
        return (
            self.ai_enabled
            and bool(self.openai_api_key)
            and bool(self.openai_model)
            and bool(self.openai_base_url)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()