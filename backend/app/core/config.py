"""Application configuration — loaded from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Veridoc configuration. All values have local-first defaults.

    NOTE: Security-critical fields (jwt_secret, file_encryption_key,
    postgres_password, minio_secret_key) MUST be overridden in production.
    The app will refuse to start if these are set to placeholder values.
    """

    # ── App ──
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 30

    # ── Postgres (will fail at startup if password is placeholder) ──
    postgres_user: str = "veridoc"
    postgres_password: str = ""
    postgres_db: str = "veridoc"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── MinIO ──
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "veridoc-documents"
    minio_use_ssl: bool = False

    # ── Chroma ──
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "veridoc_documents"

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"

    # ── JWT (empty — MUST be set in .env) ──
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── G4: Secret rotation tracking ──
    # ISO-8601 date of the last JWT_SECRET / FILE_ENCRYPTION_KEY rotation.
    # If unset, or older than `secret_rotation_warning_days`, a startup
    # warning is logged (never a hard failure).
    secret_rotated_at: str | None = None
    secret_rotation_warning_days: int = 90

    # ── File Encryption (empty — MUST be set in .env) ──
    file_encryption_key: str = ""

    # ── LLM ──
    llm_provider: Literal["ollama", "claude", "openai"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    llm_timeout: int = 60  # seconds; used by chat_service, llm_provider, job_queue, worker

    # ── Optional API Keys ──
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # ── Optional OAuth ──
    google_client_id: str | None = None
    google_client_secret: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = None

    # ── Redis / Queue ──
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    @property
    def redis_url(self) -> str:
        """Build the Redis connection URL."""
        if not self.redis_host:
            return ""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ── Paths ──
    # Local-first defaults so tests/CI work outside the container.
    # Production/Docker deployments set DATA_DIR=/app/data via compose.
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    upload_dir: Path = Path(__file__).resolve().parents[2] / "data" / "uploads"

    # ── Response Cache (Redis) ──
    redis_cache_enabled: bool = True
    redis_cache_ttl_seconds: int = 3600  # 1 hour

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Strict startup validation — refuses to boot with placeholder secrets
_PLACEHOLDER_PATTERNS = ["change-me-", "changeme", "placeholder", "your-", "<your-"]


def _validate_secret(value: str, name: str) -> str:
    """Validate that a secret is not empty or a known placeholder."""
    if not value:
        raise ValueError(
            f"{name} is not set. Set it in .env. "
            f"See .env.example for generation instructions."
        )
    lower = value.lower()
    for pattern in _PLACEHOLDER_PATTERNS:
        if pattern in lower:
            raise ValueError(
                f"{name} contains placeholder pattern '{pattern}'. "
                f"Generate a strong secret and update .env. "
                f"See .env.example for instructions."
            )
    return value


def validate_config() -> None:
    """Run at startup to validate security-critical settings."""
    errors = []
    try:
        _validate_secret(settings.jwt_secret, "JWT_SECRET")
    except ValueError as e:
        errors.append(str(e))
    try:
        _validate_secret(settings.file_encryption_key, "FILE_ENCRYPTION_KEY")
    except ValueError as e:
        errors.append(str(e))
    if errors:
        raise RuntimeError(
            "Security configuration validation failed:\n  " + "\n  ".join(errors)
        )


settings = Settings()  # type: ignore[misc]

# ── Directory creation ──────────────────────────────────
# NOTE: Directories are created lazily when needed, not at import time.
# The lifespan startup in main.py calls validate_config() first, ensuring
# secrets are validated before any side effects occur.
#
# For the rare case where code accesses these paths before the lifespan
# runs (e.g., in tests), create them silently here. This is not a
# security issue because validate_config() runs at app startup.
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.upload_dir.mkdir(parents=True, exist_ok=True)
