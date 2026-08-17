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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
