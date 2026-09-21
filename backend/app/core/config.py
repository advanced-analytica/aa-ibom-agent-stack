"""Application configuration using Pydantic BaseSettings."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

import json
from pathlib import Path
from typing import Literal
from urllib.parse import quote, urlencode

from pydantic import computed_field, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> Path | None:
    """Find .env file in current or parent directories."""
    current = Path.cwd()
    for path in [current, current.parent]:
        env_file = path / ".env"
        if env_file.exists():
            return env_file
    return None


def _parse_env_list(value: object) -> object:
    """Accept JSON arrays or comma-separated strings for list settings."""
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        return json.loads(stripped)
    return [item.strip() for item in stripped.split(",") if item.strip()]


def _quote_db_part(value: str) -> str:
    """Quote database URL user/password parts while preserving plain env values."""
    return quote(value, safe="")


def _db_query(params: dict[str, str]) -> str:
    filtered = {key: value for key, value in params.items() if value}
    return f"?{urlencode(filtered)}" if filtered else ""


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=find_env_file(),
        env_ignore_empty=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "ibom_ai_agent_stack"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    DB_ECHO: bool = (
        False  # Set DB_ECHO=true to log SQL queries (latency + log-noise drain by default)
    )
    ENVIRONMENT: Literal["development", "local", "staging", "production"] = "local"
    TIMEZONE: str = (
        "Europe/London"  # IANA timezone (e.g. "UTC", "Europe/Warsaw", "America/New_York")
    )
    MODELS_CACHE_DIR: Path = Path("./models_cache")
    MEDIA_DIR: Path = Path("./media")
    MAX_UPLOAD_SIZE_MB: int = 50  # Max file upload size in MB
    # Soft per-org storage cap surfaced on /billing — not enforced yet (5 GB).
    STORAGE_SOFT_LIMIT_BYTES: int = 5 * 1024 * 1024 * 1024

    LOGFIRE_TOKEN: str | None = None
    LOGFIRE_SERVICE_NAME: str = "ibom_ai_agent_stack"
    LOGFIRE_ENVIRONMENT: str = "development"

    POSTGRES_HOST: str = "aws-1-eu-west-1.pooler.supabase.com"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres.<project-ref>"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "postgres"
    POSTGRES_SSLMODE: str = "require"
    POSTGRES_ASYNCPG_SSL: str = "require"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Build async PostgreSQL connection URL."""
        query = _db_query({"ssl": self.POSTGRES_ASYNCPG_SSL})
        return (
            f"postgresql+asyncpg://{_quote_db_part(self.POSTGRES_USER)}:"
            f"{_quote_db_part(self.POSTGRES_PASSWORD)}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}{query}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Build sync PostgreSQL connection URL (for Alembic)."""
        query = _db_query({"sslmode": self.POSTGRES_SSLMODE})
        return (
            f"postgresql://{_quote_db_part(self.POSTGRES_USER)}:"
            f"{_quote_db_part(self.POSTGRES_PASSWORD)}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}{query}"
        )

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate SECRET_KEY is secure in production."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-in-production-use-openssl-rand-hex-32" and env == "production":
            raise ValueError(
                "SECRET_KEY must be changed in production! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        return v

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # Public URL of the frontend; used to build OAuth redirect targets and
    # Stripe checkout/portal return URLs. Always declared (not gated) because
    # the billing model_validator references it unconditionally.
    FRONTEND_URL: str = "https://localhost:3000"
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = "https://localhost:3000/auth/callback"
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""

    API_KEY: str = "change-me-in-production"
    API_KEY_HEADER: str = "X-API-Key"

    @field_validator("API_KEY")
    @classmethod
    def validate_api_key(cls, v: str, info: ValidationInfo) -> str:
        """Validate API_KEY is set in production."""
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if v == "change-me-in-production" and env == "production":
            raise ValueError(
                "API_KEY must be changed in production! "
                "Generate a secure key with: openssl rand -hex 32"
            )
        return v

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        """Build Redis connection URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    S3_ENDPOINT: str | None = None
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "ibom_ai_agent_stack"
    S3_REGION: str = "us-east-1"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    CHAT_PROVIDER: str = "gemini"
    CHAT_MODEL: str = "gemini-2.5-flash"
    CHAT_ENABLED_PROVIDERS: list[str] = ["gemini"]
    CHAT_ANTHROPIC_MODELS: list[str] = [
        "claude-sonnet-4-5",
        "claude-opus-4-1",
        "claude-haiku-4-5",
    ]
    CHAT_OPENAI_MODELS: list[str] = [
        "gpt-5.4-mini",
        "gpt-5.4",
        "gpt-4.1-mini",
    ]
    CHAT_GEMINI_MODELS: list[str] = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
    ]
    # Legacy aliases kept for existing callers and persisted conversations.
    AI_MODEL: str = "gemini-2.5-flash"
    AI_TEMPERATURE: float = 0.7
    AI_THINKING_ENABLED: bool = False
    AI_THINKING_EFFORT: str = "medium"  # "low", "medium", "high"
    AI_AVAILABLE_MODELS: list[str] = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
    ]
    AI_FRAMEWORK: str = "pydantic_ai"
    LLM_PROVIDER: str = "gemini"

    TAVILY_API_KEY: str = ""

    ENABLE_DEEP_RESEARCH: bool = False
    DEEP_RESEARCH_MAX_TOKENS: int = 120_000
    DEEP_RESEARCH_COMPRESS_THRESHOLD: float = 0.8
    # Vector Database (pgvector) — uses existing PostgreSQL
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL: str = "gemini-embedding-exp-03-07"

    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 50

    RAG_DEFAULT_COLLECTION: str = "documents"
    RAG_TOP_K: int = 10
    RAG_CHUNKING_STRATEGY: str = "recursive"  # recursive, markdown, or fixed
    RAG_HYBRID_SEARCH: bool = False  # Enable BM25 + vector hybrid search
    RAG_ENABLE_OCR: bool = False  # OCR fallback for scanned PDFs (requires tesseract)

    CORS_ORIGINS: list[str] = [
        "https://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """Warn if CORS_ORIGINS is too permissive in production."""
        env = info.data.get("ENVIRONMENT", "local") if info.data else "local"
        if "*" in v and env == "production":
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' in production! Specify explicit allowed origins."
            )
        return v

    @field_validator(
        "CHAT_ENABLED_PROVIDERS",
        "CHAT_ANTHROPIC_MODELS",
        "CHAT_OPENAI_MODELS",
        "CHAT_GEMINI_MODELS",
        "AI_AVAILABLE_MODELS",
        mode="before",
    )
    @classmethod
    def parse_list_settings(cls, v: object) -> object:
        """Allow either JSON arrays or comma-separated strings in env files."""
        return _parse_env_list(v)

    @field_validator("CHAT_PROVIDER", "EMBEDDING_PROVIDER", "LLM_PROVIDER")
    @classmethod
    def normalize_provider_name(cls, v: str) -> str:
        provider = (v or "").strip().lower()
        if provider == "google":
            return "gemini"
        return provider

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rag(self) -> "RAGSettings":
        """Build RAG-specific settings."""
        pdf_parser = PdfParser()

        return RAGSettings(
            collection_name=self.RAG_DEFAULT_COLLECTION,
            chunk_size=self.RAG_CHUNK_SIZE,
            chunk_overlap=self.RAG_CHUNK_OVERLAP,
            chunking_strategy=self.RAG_CHUNKING_STRATEGY,
            enable_hybrid_search=self.RAG_HYBRID_SEARCH,
            enable_ocr=self.RAG_ENABLE_OCR,
            embeddings_config=EmbeddingsConfig(
                provider=self.EMBEDDING_PROVIDER,
                model=self.EMBEDDING_MODEL,
            ),
            document_parser=DocumentParser(),
            pdf_parser=pdf_parser,
        )


# Rebuild Settings to resolve RAGSettings forward reference
from app.services.rag.config import DocumentParser, EmbeddingsConfig, PdfParser, RAGSettings

Settings.model_rebuild()


settings = Settings()
