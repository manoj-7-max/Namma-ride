from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app

client = TestClient(app)


def test_live_and_pilot_boundaries():
    assert client.get("/health/live").json() == {"status": "ok"}
    data = client.get("/api/v1/pilot").json()
    assert (
        data["phase"],
        data["location"],
        data["customer_limit"],
        data["driver_limit"],
    ) == (3, "Madurantakam", 100, 10)
    assert data["payment_processing_enabled"] is False
    assert data["public_ride_operations_enabled"] is False
    assert data["bike_taxi_mode"] == "demo_only"


def test_readiness_failure_is_sanitized(monkeypatch):
    def fail():
        raise SQLAlchemyError("secret database password")

    monkeypatch.setattr("app.main.get_engine", fail)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert "secret" not in response.text
