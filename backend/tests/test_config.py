import pytest
from pydantic import ValidationError

from app.config import Settings


def test_secrets_are_required_and_not_logged():
    config = Settings(
        _env_file=None,
        db_password="private-db-password-for-tests",
        admin_api_key="private-admin-key-for-tests-at-least-32-chars",
        jwt_secret="private-jwt-secret-for-tests-at-least-32-chars",
        otp_pepper="private-otp-pepper-for-tests-at-least-32-chars",
        pilot_otp_admin_api_key="private-pilot-otp-admin-key-at-least-32-chars",
        pilot_otp_encryption_key="vqpmAs4Ia5oeruKt4H384Mu8lxvy1inTjGu5w2CvhLw=",
    )
    for text in (repr(config), config.model_dump_json()):
        assert "private-db-password-for-tests" not in text
        assert "private-admin-key-for-tests" not in text
        assert "private-pilot-otp-admin-key" not in text


@pytest.mark.parametrize(
    "secret", ["short", "replace-with-a-long-random-key-at-least-32"]
)
def test_weak_or_placeholder_admin_keys_are_rejected(secret):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            db_password="private-db-password-for-tests",
            admin_api_key=secret,
            jwt_secret="private-jwt-secret-for-tests-at-least-32-chars",
            otp_pepper="private-otp-pepper-for-tests-at-least-32-chars",
        )


def test_pilot_otp_keys_are_valid_and_distinct():
    common = {
        "_env_file": None,
        "db_password": "private-db-password-for-tests",
        "admin_api_key": "private-admin-key-for-tests-at-least-32-chars",
        "jwt_secret": "private-jwt-secret-for-tests-at-least-32-chars",
        "otp_pepper": "private-otp-pepper-for-tests-at-least-32-chars",
    }
    with pytest.raises(ValidationError):
        Settings(
            **common,
            pilot_otp_admin_api_key="different-pilot-key-for-tests-32-chars",
            pilot_otp_encryption_key="x" * 44,
        )
    with pytest.raises(ValidationError):
        Settings(
            **common,
            pilot_otp_admin_api_key=common["admin_api_key"],
            pilot_otp_encryption_key="vqpmAs4Ia5oeruKt4H384Mu8lxvy1inTjGu5w2CvhLw=",
        )
