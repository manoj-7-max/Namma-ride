import hmac
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import generate_otp, hash_otp, issue_token, utc_now
from app.config import get_settings
from app.database import get_db
from app.models import OTPChallenge, User
from app.schemas import OTPRequest, OTPVerify, TokenOut, UserOut
from app.services import count_role

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
ROLE_LIMITS = {"customer": 100, "driver": 10}


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        phone=user.phone,
        display_name=user.display_name,
        role=user.role,
        driver_approved=user.driver_approved,
        vehicle_number=user.vehicle_number,
    )


@router.post("/otp/request")
def request_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.phone == payload.phone))
    if existing and existing.role != payload.role:
        raise HTTPException(409, "Phone is registered for another role")
    if existing is None:
        if not payload.display_name:
            raise HTTPException(422, "Display name is required for registration")
        if payload.role == "driver" and not payload.vehicle_number:
            raise HTTPException(
                422, "Vehicle number is required for driver registration"
            )
        if count_role(db, payload.role) >= ROLE_LIMITS[payload.role]:
            raise HTTPException(409, f"Private pilot {payload.role} limit reached")
    db.execute(
        update(OTPChallenge)
        .where(OTPChallenge.phone == payload.phone, OTPChallenge.consumed_at.is_(None))
        .values(consumed_at=utc_now())
    )
    code = generate_otp()
    challenge = OTPChallenge(
        phone=payload.phone,
        role=payload.role,
        display_name=payload.display_name,
        vehicle_number=payload.vehicle_number,
        code_hash=hash_otp(payload.phone, code),
        expires_at=utc_now() + timedelta(seconds=get_settings().otp_ttl_seconds),
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    result = {
        "challenge_id": challenge.id,
        "expires_in_seconds": get_settings().otp_ttl_seconds,
    }
    if get_settings().expose_test_otp:
        result["test_otp"] = code
    return result


@router.post("/otp/verify", response_model=TokenOut)
def verify_otp(payload: OTPVerify, db: Session = Depends(get_db)):
    challenge = db.get(OTPChallenge, payload.challenge_id)
    if challenge is None or challenge.phone != payload.phone:
        raise HTTPException(400, "Invalid OTP challenge")
    if challenge.consumed_at is not None or challenge.expires_at <= utc_now():
        raise HTTPException(400, "OTP challenge expired or already used")
    if challenge.attempts >= 5:
        raise HTTPException(429, "Too many OTP attempts")
    if not hmac.compare_digest(
        challenge.code_hash, hash_otp(payload.phone, payload.otp)
    ):
        challenge.attempts += 1
        db.commit()
        raise HTTPException(400, "Invalid OTP")
    challenge.consumed_at = utc_now()
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if user is None:
        if count_role(db, challenge.role) >= ROLE_LIMITS[challenge.role]:
            raise HTTPException(409, f"Private pilot {challenge.role} limit reached")
        user = User(
            phone=challenge.phone,
            display_name=challenge.display_name or "Pilot member",
            role=challenge.role,
            vehicle_number=challenge.vehicle_number,
            driver_approved=False,
        )
        db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=issue_token(user.role, user.id), user=user_out(user))


@router.post("/admin-token", response_model=TokenOut)
def admin_token(x_admin_key: str | None = Header(default=None)):
    expected = get_settings().admin_api_key.get_secret_value()
    if not x_admin_key or not secrets.compare_digest(
        x_admin_key.encode(), expected.encode()
    ):
        raise HTTPException(401, "Invalid admin key")
    return TokenOut(access_token=issue_token("admin"))
