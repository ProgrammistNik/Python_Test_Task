from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = "test-api-key"
    database_url: str = "postgresql+asyncpg://payments:payments@localhost:5432/payments"
    rabbitmq_url: str = "amqp://payments:payments@localhost:5672/"
    processing_delay_min: float = Field(default=2, ge=0)
    processing_delay_max: float = Field(default=5, ge=0)
    webhook_timeout: float = Field(default=5, gt=0)
    outbox_poll_interval: float = Field(default=1, gt=0)


settings = Settings()
