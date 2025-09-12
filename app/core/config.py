"""Core application configuration."""

from typing import List, Optional

from pydantic import AnyHttpUrl, ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: Optional[str] = None

    # Environment
    ENVIRONMENT: str = "development"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Project metadata
    PROJECT_NAME: str = "BEA"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = "Bem Estar Acadêmico API"

    model_config = ConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
