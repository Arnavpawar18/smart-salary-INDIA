from typing import Literal

from pydantic import Field, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartSalary India"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # PostgreSQL connection (Local instance port 5433)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "smartsalary"
    DATABASE_URL: str = "postgresql+psycopg://postgres:@localhost:5433/smartsalary"

    # Test Database connection
    POSTGRES_TEST_DB: str = "smartsalary_test"
    DATABASE_URL_TEST: str = "postgresql+psycopg://postgres:@localhost:5433/smartsalary_test"

    # OTP Security & Rate Limiting
    OTP_HASH_SECRET: str = "smartsalary-otp-hmac-secret-2026"
    OTP_EXPIRE_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    DEV_EXPOSE_OTP: bool = False

    # SMTP Configuration & Reliability
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_FROM_NAME: str = "SmartSalary India"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 10
    SMTP_CONNECT_TIMEOUT_SECONDS: int = 10
    SMTP_MAX_RETRIES: int = 2
    SMTP_RETRY_BACKOFF_SECONDS: float = 1.0
    ENABLE_STARTUP_SMTP_CHECK: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class RateLimitSettings(BaseSettings):
    """Configuration for Redis connection and rate‑limit defaults."""

    RATE_LIMIT_REDIS_REQUIRED: bool = Field(False, description="Enforce Redis-backed rate limiting; if false, fallback to InMemoryRateLimiter.")

    # Existing fields follow
    # Redis connection URL – required in production
    REDIS_URL: RedisDsn | None = Field(None)
    REDIS_TIMEOUT_SECONDS: int = Field(2, ge=1, description="Socket timeout for Redis operations")

    # Environment identifier – reused from Settings for key namespacing
    ENVIRONMENT: Literal["development", "test", "production"] = Field("development")

    # Rate‑limit defaults (can be overridden per‑operation via env vars if needed)
    CALC_RATE_LIMIT: int = Field(10, ge=1, description="Maximum calculation requests per window")
    CALC_RATE_WINDOW: int = Field(60, ge=1, description="Window size in seconds for calculation limit")
    READ_RATE_LIMIT: int = Field(30, ge=1, description="Maximum read‑type requests per window")
    READ_RATE_WINDOW: int = Field(60, ge=1, description="Window size in seconds for read limits")
    # Add additional operation limits as needed


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

# Instantiate both settings objects for easy import elsewhere
rate_limit_settings = RateLimitSettings()




settings = Settings()
