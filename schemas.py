from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class InputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


def check_password(value):
    if value is not None:
        if len(value.encode("utf-8")) > 72 or "\x00" in value:
            raise ValueError("Password must be at most 72 bytes and contain no null characters.")
    return value


class UserCreate(InputSchema):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=100)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return check_password(value)


class UserUpdate(InputSchema):
    username: str | None = Field(default=None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return check_password(value)

    @model_validator(mode="after")
    def reject_null_values(self):
        for field in ("username", "email", "password"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    full_name: str | None
    disabled: bool
    role: Literal["admin", "editor", "user"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class NoteCreate(InputSchema):
    title: str = Field(min_length=1, max_length=200)
    content: str
    is_public: bool = False
    tags: list[str] = Field(default_factory=list)


class NoteUpdate(InputSchema):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = None
    is_public: bool | None = None
    tags: list[str] | None = None

    @model_validator(mode="after")
    def reject_null_values(self):
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    owner: str
    is_public: bool
    created_at: datetime
    tags: list[str]
