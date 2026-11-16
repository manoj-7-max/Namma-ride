import pytest
from pydantic import ValidationError

from app.config import Settings


def test_secrets_are_required_and_not_logged():
    config = Settings(
        _env_file=None,
        db_password="private-db-password-for-tests",
        admin_api_key="private-admin-key-for-tests-at-least-32-chars",
    )
    for text in (repr(config), config.model_dump_json()):
        assert "private-db-password-for-tests" not in text
        assert "private-admin-key-for-tests" not in text


@pytest.mark.parametrize(
    "secret", ["short", "replace-with-a-long-random-key-at-least-32"]
)
def test_weak_or_placeholder_admin_keys_are_rejected(secret):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            db_password="private-db-password-for-tests",
            admin_api_key=secret,
        )
