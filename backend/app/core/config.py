"""Application configuration — loaded from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Veridoc configuration. All values have local-first defaults."""

    # ── App ──
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 30

    # ── Postgres ──
    postgres_user: str = "veridoc"
    postgres_password: str = "veridoc_local_dev"
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
    minio_access_key: str = "veridoc"
    minio_secret_key: str = "veridoc_minio_dev"
    minio_bucket: str = "veridoc-documents"
    minio_use_ssl: bool = False

    # ── Chroma ──
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "veridoc_documents"

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"

    # ── JWT ──
    jwt_secret: str = "change-me-to-a-random-64-char-string-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── File Encryption ──
    file_encryption_key: str = "change-me-to-a-32-byte-base64-key"

    # ── LLM ──
    llm_provider: Literal["ollama", "claude", "openai"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # ── Optional API Keys ──
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # ── Optional OAuth ──
    google_client_id: str | None = None
    google_client_secret: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = None

    # ── Paths ──
    data_dir: Path = Path("/app/data")
    upload_dir: Path = Path("/app/data/uploads")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

# Ensure data directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.upload_dir.mkdir(parents=True, exist_ok=True)
