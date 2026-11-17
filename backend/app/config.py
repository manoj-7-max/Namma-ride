from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator, model_validator
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
    pilot_otp_admin_api_key: SecretStr = Field(min_length=32)
    pilot_otp_encryption_key: SecretStr = Field(min_length=44, max_length=44)
    expose_test_otp: bool = False
    otp_ttl_seconds: int = Field(default=300, ge=60, le=900)
    otp_request_limit: int = Field(default=5, ge=1, le=20)
    otp_request_window_seconds: int = Field(default=900, ge=60, le=3600)
    jwt_ttl_minutes: int = Field(default=720, ge=15, le=1440)
    matching_radius_km: float = Field(default=8.0, gt=0, le=25)
    location_max_age_seconds: int = Field(default=120, ge=30, le=600)
    location_max_accuracy_m: float = Field(default=100.0, gt=0, le=500)
    location_min_interval_seconds: int = Field(default=5, ge=1, le=60)
    dispatch_offer_seconds: int = Field(default=30, ge=10, le=120)
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator(
        "db_password",
        "admin_api_key",
        "jwt_secret",
        "otp_pepper",
        "pilot_otp_admin_api_key",
        "pilot_otp_encryption_key",
    )
    @classmethod
    def reject_example_secrets(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value().startswith("replace-"):
            raise ValueError("Generate a random secret; do not use the example value")
        return value

    @field_validator("pilot_otp_encryption_key")
    @classmethod
    def validate_fernet_key(cls, value: SecretStr) -> SecretStr:
        try:
            Fernet(value.get_secret_value().encode())
        except (TypeError, ValueError):
            raise ValueError("PILOT_OTP_ENCRYPTION_KEY must be a Fernet key") from None
        return value

    @model_validator(mode="after")
    def require_distinct_admin_keys(self):
        if secrets_equal(self.admin_api_key, self.pilot_otp_admin_api_key):
            raise ValueError("Pilot OTP and general administrator keys must differ")
        return self


def secrets_equal(left: SecretStr, right: SecretStr) -> bool:
    return left.get_secret_value() == right.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
