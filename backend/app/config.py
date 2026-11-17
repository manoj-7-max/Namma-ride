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
    jwt_secret: SecretStr = Field(min_length=32)
    otp_pepper: SecretStr = Field(min_length=32)
    expose_test_otp: bool = False
    otp_ttl_seconds: int = Field(default=300, ge=60, le=900)
    jwt_ttl_minutes: int = Field(default=720, ge=15, le=1440)
    matching_radius_km: float = Field(default=8.0, gt=0, le=25)
    location_max_age_seconds: int = Field(default=120, ge=30, le=600)
    location_max_accuracy_m: float = Field(default=100.0, gt=0, le=500)
    location_min_interval_seconds: int = Field(default=5, ge=1, le=60)
    dispatch_offer_seconds: int = Field(default=30, ge=10, le=120)
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("db_password", "admin_api_key", "jwt_secret", "otp_pepper")
    @classmethod
    def reject_example_secrets(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value().startswith("replace-"):
            raise ValueError("Generate a random secret; do not use the example value")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
