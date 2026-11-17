import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    role: str
    user: User | None


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(phone: str, otp: str) -> str:
    pepper = get_settings().otp_pepper.get_secret_value().encode()
    return hmac.new(pepper, f"{phone}:{otp}".encode(), hashlib.sha256).hexdigest()


def issue_token(role: str, user_id: int | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id) if user_id is not None else "admin",
        "role": role,
        "iss": "namma-ride-private-test",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm="HS256"
    )


def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Principal:
    if credentials is None:
        raise HTTPException(401, "Bearer token required")
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_settings().jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            issuer="namma-ride-private-test",
        )
        role, subject = payload["role"], payload["sub"]
    except (InvalidTokenError, KeyError):
        raise HTTPException(401, "Invalid or expired token") from None
    if role == "admin" and subject == "admin":
        return Principal(role="admin", user=None)
    user = db.get(User, int(subject)) if str(subject).isdigit() else None
    if user is None or user.role != role:
        raise HTTPException(401, "User no longer exists")
    return Principal(role=role, user=user)


def require_role(*roles: str):
    def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if principal.role not in roles:
            raise HTTPException(403, "Role not permitted")
        return principal

    return dependency
