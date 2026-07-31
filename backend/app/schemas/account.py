from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class AccountSignup(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def passwords_match(self) -> "AccountSignup":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class AccountLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AccountResponse(BaseModel):
    id: int
    full_name: str
    email: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    message: str
    account: AccountResponse
