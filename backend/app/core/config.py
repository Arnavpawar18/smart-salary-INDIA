from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartSalary India"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # PostgreSQL connection
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "smartsalary"
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smartsalary"

    # Test Database connection
    POSTGRES_TEST_DB: str = "smartsalary_test"
    DATABASE_URL_TEST: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smartsalary_test"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
