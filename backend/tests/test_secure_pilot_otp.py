from datetime import timedelta

from conftest import engine
from fastapi.testclient import TestClient
from otp_helpers import pilot_otp_headers
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import utc_now
from app.config import get_settings
from app.main import app
from app.models import AuditLog, OTPChallenge, PilotOTPDelivery

client = TestClient(app)
PHONE = "9876543290"


def payload(phone=PHONE):
    return {"phone": phone, "role": "customer", "display_name": "Pilot Tester"}


def approve(phone=PHONE):
    response = client.put(
        "/api/v1/admin/pilot-otp/recipients",
        headers=pilot_otp_headers(client),
        json={"phone": phone, "active": True},
    )
    assert response.status_code == 200


def request_and_retrieve(phone=PHONE):
    approve(phone)
    requested = client.post("/api/v1/auth/otp/request", json=payload(phone))
    challenge = requested.json()
    retrieved = client.post(
        f"/api/v1/admin/pilot-otp/challenges/{challenge['challenge_id']}/retrieve",
        headers=pilot_otp_headers(client),
        json={"phone": phone},
    )
    return requested, retrieved


def test_public_request_never_returns_otp_and_unapproved_is_not_retrievable():
    settings = get_settings()
    original = settings.expose_test_otp
    settings.expose_test_otp = True  # Legacy flag must not alter the public response.
    try:
        requested = client.post("/api/v1/auth/otp/request", json=payload())
    finally:
        settings.expose_test_otp = original
    assert requested.status_code == 200
    assert set(requested.json()) == {"challenge_id", "expires_in_seconds"}
    challenge_id = requested.json()["challenge_id"]
    approve()
    denied = client.post(
        f"/api/v1/admin/pilot-otp/challenges/{challenge_id}/retrieve",
        headers=pilot_otp_headers(client),
        json={"phone": PHONE},
    )
    assert denied.status_code == 404


def test_invalid_or_ordinary_admin_cannot_manage_or_retrieve_otp():
    assert (
        client.post(
            "/api/v1/auth/pilot-otp-admin-token",
            headers={"X-Pilot-Otp-Admin-Key": "invalid"},
        ).status_code
        == 401
    )
    ordinary = client.post(
        "/api/v1/auth/admin-token",
        headers={"X-Admin-Key": get_settings().admin_api_key.get_secret_value()},
    ).json()["access_token"]
    denied = client.put(
        "/api/v1/admin/pilot-otp/recipients",
        headers={"Authorization": f"Bearer {ordinary}"},
        json={"phone": PHONE, "active": True},
    )
    assert denied.status_code == 403
    assert (
        client.put(
            "/api/v1/admin/pilot-otp/recipients",
            json={"phone": PHONE, "active": True},
        ).status_code
        == 401
    )


def test_encrypted_delivery_is_one_time_hashed_and_audited():
    requested, retrieved = request_and_retrieve()
    assert requested.status_code == 200 and retrieved.status_code == 200
    code = retrieved.json()["otp"]
    assert len(code) == 6 and code.isdigit()
    assert retrieved.headers["cache-control"] == "no-store"
    challenge_id = requested.json()["challenge_id"]
    with Session(engine) as db:
        challenge = db.get(OTPChallenge, challenge_id)
        delivery = db.scalar(
            select(PilotOTPDelivery).where(
                PilotOTPDelivery.challenge_id == challenge_id
            )
        )
        assert challenge.code_hash != code and code not in delivery.encrypted_code
        assert db.scalar(
            select(AuditLog).where(
                AuditLog.action == "pilot_otp.retrieved",
                AuditLog.target_id == challenge_id,
            )
        )
    replay = client.post(
        f"/api/v1/admin/pilot-otp/challenges/{challenge_id}/retrieve",
        headers=pilot_otp_headers(client),
        json={"phone": PHONE},
    )
    assert replay.status_code == 404
    verified = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": challenge_id, "phone": PHONE, "otp": code},
    )
    assert verified.status_code == 200


def test_expired_delivery_is_deleted_and_cannot_be_retrieved():
    approve()
    requested = client.post("/api/v1/auth/otp/request", json=payload()).json()
    with Session(engine) as db:
        delivery = db.scalar(
            select(PilotOTPDelivery).where(
                PilotOTPDelivery.challenge_id == requested["challenge_id"]
            )
        )
        delivery.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    response = client.post(
        f"/api/v1/admin/pilot-otp/challenges/{requested['challenge_id']}/retrieve",
        headers=pilot_otp_headers(client),
        json={"phone": PHONE},
    )
    assert response.status_code == 404
    with Session(engine) as db:
        assert (
            db.scalar(
                select(PilotOTPDelivery).where(
                    PilotOTPDelivery.challenge_id == requested["challenge_id"]
                )
            )
            is None
        )


def test_verification_locks_after_five_failures():
    approve()
    challenge = client.post("/api/v1/auth/otp/request", json=payload()).json()
    invalid = {
        "challenge_id": challenge["challenge_id"],
        "phone": PHONE,
        "otp": "000000",
    }
    for _ in range(5):
        assert client.post("/api/v1/auth/otp/verify", json=invalid).status_code == 400
    assert client.post("/api/v1/auth/otp/verify", json=invalid).status_code == 429
