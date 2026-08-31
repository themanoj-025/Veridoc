"""Tests for Veridoc Pydantic schemas."""

import uuid
from datetime import datetime

import pytest
from app.schemas.auth import UserCreate, UserLogin, UserResponse
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from pydantic import ValidationError


class TestUserCreate:
    """Tests for UserCreate schema."""

    def test_valid_user(self) -> None:
        user = UserCreate(email="test@example.com", password="Str0ngP@ss1")
        assert user.email == "test@example.com"

    def test_with_full_name(self) -> None:
        user = UserCreate(email="test@example.com", password="Str0ngP@ss1", full_name="John Doe")
        assert user.full_name == "John Doe"

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email", password="Str0ngP@ss1")

    def test_short_password(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="Ab1!")

    def test_long_password(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="A" * 129 + "1a")


class TestUserLogin:
    """Tests for UserLogin schema."""

    def test_valid_login(self) -> None:
        login = UserLogin(email="user@test.com", password="pass123")
        assert login.email == "user@test.com"

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            UserLogin(email="bad", password="pass")


class TestUserResponse:
    """Tests for UserResponse schema."""

    def test_from_attributes(self) -> None:
        resp = UserResponse(
            id=uuid.uuid4(),
            email="test@example.com",
            full_name="Test",
            is_active=True,
            is_verified=False,
            created_at=datetime.now(),
        )
        assert resp.is_active is True


class TestDocumentUploadResponse:
    """Tests for DocumentUploadResponse schema."""

    def test_valid_response(self) -> None:
        resp = DocumentUploadResponse(
            id=uuid.uuid4(),
            title="Test Doc",
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            status="pending",
            created_at=datetime.now(),
        )
        assert resp.file_size == 1024


class TestDocumentResponse:
    """Tests for DocumentResponse schema."""

    def test_valid_response(self) -> None:
        resp = DocumentResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Test",
            filename="test.pdf",
            file_type="application/pdf",
            file_size=1024,
            status="completed",
            ocr_used=False,
            page_count=5,
            chunk_count=10,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert resp.page_count == 5
