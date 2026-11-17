"""Smoke-check a migrated test DB and HTTP admin access; never writes records."""

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def main():
    client = TestClient(app)
    assert client.get("/health/ready").status_code == 200
    assert client.get("/api/v1/admin/summary").status_code == 401
    response = client.get(
        "/api/v1/admin/summary",
        headers={"X-Admin-Key": get_settings().admin_api_key.get_secret_value()},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["customer_limit"] == 100 and data["driver_limit"] == 10
    print("Migrated PostgreSQL readiness and authorized summary passed.")


if __name__ == "__main__":
    main()
