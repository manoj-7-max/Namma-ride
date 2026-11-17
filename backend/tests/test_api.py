import os

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app

TEST_ADMIN_KEY = os.environ["ADMIN_API_KEY"]
client = TestClient(app)


def test_live():
    assert client.get("/health/live").json() == {"status": "ok"}


def test_pilot_scope():
    data = client.get("/api/v1/pilot").json()
    assert (data["location"], data["customer_limit"], data["driver_limit"]) == (
        "Madurantakam",
        100,
        10,
    )


def test_pilot_has_no_real_operations():
    data = client.get("/api/v1/pilot").json()
    assert data["state"] == "Tamil Nadu"
    assert data["mode"] == "private_test"
    assert data["public_ride_operations_enabled"] is False
    assert data["payment_processing_enabled"] is False
    assert data["bike_taxi_mode"] == "demo_only"


def test_admin_rejects_missing_and_wrong_keys():
    for headers in ({}, {"X-Admin-Key": "wrong"}):
        assert client.get("/api/v1/admin/summary", headers=headers).status_code == 401


def test_database_failure_is_sanitized(monkeypatch):
    def fail():
        raise SQLAlchemyError("secret database password")

    monkeypatch.setattr("app.main.get_engine", fail)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert "secret" not in response.text
    assert (
        client.get(
            "/api/v1/admin/summary", headers={"X-Admin-Key": TEST_ADMIN_KEY}
        ).status_code
        == 503
    )
