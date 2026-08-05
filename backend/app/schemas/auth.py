"""Pydantic schemas for authentication."""

import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.core.security import validate_password_complexity


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None

    @model_validator(mode="after")
    def _check_password_complexity(self) -> Self:
        err = validate_password_complexity(self.password)
        if err:
            raise ValueError(err)
        return self


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefresh(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def _check_password_complexity(self) -> Self:
        err = validate_password_complexity(self.new_password)
        if err:
            raise ValueError(err)
        return self
