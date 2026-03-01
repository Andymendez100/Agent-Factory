from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/agent_factory"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Encryption
    FERNET_KEY: str = ""

    # SMTP (for send_alert tool)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Mock Portal
    MOCK_PORTAL_URL: str = "http://mock-portal:8001"
    MOCK_PORTAL_USERNAME: str = "admin"
    MOCK_PORTAL_PASSWORD: str = "demo123"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
