from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def _cipher() -> Fernet:
    return Fernet(get_settings().pilot_otp_encryption_key.get_secret_value().encode())


def encrypt_otp(code: str) -> str:
    return _cipher().encrypt(code.encode()).decode()


def decrypt_otp(value: str) -> str:
    try:
        return _cipher().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("OTP delivery ciphertext is invalid") from exc
