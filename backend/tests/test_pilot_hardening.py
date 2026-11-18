from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from otp_helpers import request_pilot_otp

from app.config import get_settings
from app.main import app

client = TestClient(app)


def register(role: str, phone: str, name: str, vehicle: str | None = None):
    payload = {"phone": phone, "role": role, "display_name": name}
    if vehicle:
        payload["vehicle_number"] = vehicle
    challenge, code = request_pilot_otp(client, payload)
    return client.post(
        "/api/v1/auth/otp/verify",
        json={
            "challenge_id": challenge["challenge_id"],
            "phone": phone,
            "otp": code,
        },
    ).json()


def bearer(result):
    return {"Authorization": f"Bearer {result['access_token']}"}


def admin_headers():
    token = client.post(
        "/api/v1/auth/admin-token",
        headers={"X-Admin-Key": get_settings().admin_api_key.get_secret_value()},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_otp_request_rate_limit():
    payload = {
        "phone": "9876543230",
        "role": "customer",
        "display_name": "Rate Limit",
    }
    for _ in range(get_settings().otp_request_limit):
        assert client.post("/api/v1/auth/otp/request", json=payload).status_code == 200
    blocked = client.post("/api/v1/auth/otp/request", json=payload)
    assert blocked.status_code == 429
    assert "try again later" in blocked.json()["detail"]


def test_duplicate_active_booking_is_rejected_but_history_remains():
    customer = register("customer", "9876543231", "One Ride")
    payload = {
        "pickup": "Madurantakam Bus Stand",
        "dropoff": "Madurantakam Railway Station",
        "estimated_distance_km": 3,
    }
    first = client.post("/api/v1/rides", headers=bearer(customer), json=payload)
    assert first.status_code == 201
    duplicate = client.post("/api/v1/rides", headers=bearer(customer), json=payload)
    assert duplicate.status_code == 409
    assert len(client.get("/api/v1/rides/mine", headers=bearer(customer)).json()) == 1


def test_admin_customer_deactivation_driver_suspension_and_audit():
    customer = register("customer", "9876543232", "Managed Customer")
    driver = register("driver", "9876543233", "Managed Driver", "TN19EF6666")
    admin = admin_headers()
    customers = client.get("/api/v1/admin/customers", headers=admin)
    assert customers.status_code == 200
    assert customers.json()[0]["phone"] == "+919876543232"
    deactivated = client.patch(
        f"/api/v1/admin/customers/{customer['user']['id']}/active",
        headers=admin,
        json={"active": False},
    )
    assert deactivated.status_code == 200
    assert client.get("/api/v1/rides/mine", headers=bearer(customer)).status_code == 403
    suspended = client.patch(
        f"/api/v1/admin/drivers/{driver['user']['id']}/suspension",
        headers=admin,
        json={"suspended": True},
    )
    assert suspended.status_code == 200 and suspended.json()["suspended"] is True
    assert client.get("/api/v1/rides/mine", headers=bearer(driver)).status_code == 403
    audit = client.get("/api/v1/admin/audit", headers=admin).json()
    assert {entry["action"] for entry in audit} >= {
        "customer.active_changed",
        "driver.suspension_changed",
    }


def test_expired_and_unsigned_tokens_are_rejected():
    expired = jwt.encode(
        {
            "sub": "1",
            "role": "customer",
            "iss": "namma-ride-private-test",
            "iat": datetime.now(UTC) - timedelta(hours=2),
            "exp": datetime.now(UTC) - timedelta(hours=1),
        },
        get_settings().jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    assert (
        client.get(
            "/api/v1/rides/mine", headers={"Authorization": f"Bearer {expired}"}
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/rides/mine", headers={"Authorization": "Bearer not-a-jwt"}
        ).status_code
        == 401
    )
