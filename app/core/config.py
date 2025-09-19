from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    database_url: str = Field(..., env="DATABASE_URL")
    test_database_url: Optional[str] = Field(default=None, env="TEST_DATABASE_URL")
    environment: str = Field(default="development", env="ENVIRONMENT")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0", env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND"
    )
    smtp_server: Optional[str] = Field(default=None, env="SMTP_SERVER")
    smtp_port: Optional[int] = Field(default=587, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


settings = Settings()
