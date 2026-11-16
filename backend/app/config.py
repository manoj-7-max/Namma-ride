from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True
    )
    db_host: str = "localhost"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "namma_ride"
    db_user: str = "namma"
    db_password: SecretStr = Field(min_length=16)
    admin_api_key: SecretStr = Field(min_length=32)
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("db_password", "admin_api_key")
    @classmethod
    def reject_example_secrets(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value().startswith("replace-"):
            raise ValueError("Generate a random secret; do not use the example value")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
