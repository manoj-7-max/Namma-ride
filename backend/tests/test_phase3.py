from datetime import UTC, datetime, timedelta

from conftest import engine
from fastapi.testclient import TestClient
from otp_helpers import request_pilot_otp
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.main import app
from app.models import RideDispatch

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


def approve(driver):
    response = client.patch(
        f"/api/v1/admin/drivers/{driver['user']['id']}/approval",
        headers=admin_headers(),
        json={"approved": True},
    )
    assert response.status_code == 200


def location(latitude=12.508, longitude=79.884, **overrides):
    result = {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy_m": 15,
        "captured_at": datetime.now(UTC).isoformat(),
        "available": True,
    }
    result.update(overrides)
    return result


def test_location_validation_availability_radius_and_permissions():
    customer = register("customer", "9876543220", "Vani")
    driver = register("driver", "9876543221", "Arun", "TN19EF1111")
    approve(driver)
    customer_headers, driver_headers = bearer(customer), bearer(driver)
    assert (
        client.put(
            "/api/v1/driver/location",
            headers=customer_headers,
            json=location(),
        ).status_code
        == 403
    )
    stale = location(
        captured_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    )
    assert (
        client.put(
            "/api/v1/driver/location", headers=driver_headers, json=stale
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/v1/driver/location",
            headers=driver_headers,
            json=location(accuracy_m=250),
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/v1/driver/location",
            headers=driver_headers,
            json=location(),
        ).status_code
        == 200
    )
    nearby = client.get(
        "/api/v1/drivers/nearby?latitude=12.508&longitude=79.884",
        headers=customer_headers,
    ).json()
    assert nearby["available_count"] == 1
    far = client.get(
        "/api/v1/drivers/nearby?latitude=13.1&longitude=80.2",
        headers=customer_headers,
    ).json()
    assert far["available_count"] == 0


def test_matching_offer_double_assignment_tracking_and_events():
    customer = register("customer", "9876543222", "Malar")
    first = register("driver", "9876543223", "Devi", "TN19EF2222")
    second = register("driver", "9876543224", "Bala", "TN19EF3333")
    approve(first)
    approve(second)
    for driver, lat in ((first, 12.508), (second, 12.53)):
        response = client.put(
            "/api/v1/driver/location",
            headers=bearer(driver),
            json=location(latitude=lat),
        )
        assert response.status_code == 200
    ride = client.post(
        "/api/v1/rides",
        headers=bearer(customer),
        json={
            "pickup": "Madurantakam Bus Stand",
            "dropoff": "Railway Station",
            "estimated_distance_km": 3,
            "pickup_latitude": 12.508,
            "pickup_longitude": 79.884,
            "dropoff_latitude": 12.51,
            "dropoff_longitude": 79.89,
        },
    ).json()
    assert ride["status"] == "matching"
    assert (
        client.get(
            f"/api/v1/rides/{ride['id']}/driver-location",
            headers=bearer(customer),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/driver/requests/{ride['id']}/accept",
            headers=bearer(second),
        ).status_code
        == 409
    )
    accepted = client.post(
        f"/api/v1/driver/requests/{ride['id']}/accept",
        headers=bearer(first),
    )
    assert accepted.status_code == 200
    assert accepted.json()["driver_location"] is not None
    assert accepted.json()["driver_eta_minutes"] >= 1
    assert (
        client.post(
            f"/api/v1/driver/requests/{ride['id']}/accept",
            headers=bearer(second),
        ).status_code
        == 409
    )
    assert (
        client.get(
            f"/api/v1/rides/{ride['id']}/driver-location",
            headers=bearer(customer),
        ).status_code
        == 200
    )
    outsider = register("customer", "9876543225", "Ravi")
    assert (
        client.get(
            f"/api/v1/rides/{ride['id']}/events", headers=bearer(outsider)
        ).status_code
        == 403
    )
    events = client.get(
        f"/api/v1/rides/{ride['id']}/events", headers=bearer(customer)
    ).json()
    assert {event["event_type"] for event in events} >= {
        "ride_requested",
        "driver_offered",
        "ride_accepted",
    }


def test_no_driver_available_and_rematch_state():
    customer = register("customer", "9876543226", "Uma")
    response = client.post(
        "/api/v1/rides",
        headers=bearer(customer),
        json={
            "pickup": "Far pickup",
            "dropoff": "Far dropoff",
            "estimated_distance_km": 2,
            "pickup_latitude": 11.0,
            "pickup_longitude": 78.0,
            "dropoff_latitude": 11.01,
            "dropoff_longitude": 78.01,
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "no_driver_available"
    rematch = client.post(
        f"/api/v1/rides/{response.json()['id']}/rematch", headers=bearer(customer)
    )
    assert rematch.status_code == 200
    assert rematch.json()["status"] == "no_driver_available"


def test_expired_offer_retries_next_nearest_driver():
    customer = register("customer", "9876543227", "Nila")
    first = register("driver", "9876543228", "Kumar", "TN19EF4444")
    second = register("driver", "9876543229", "Jaya", "TN19EF5555")
    approve(first)
    approve(second)
    for driver, lat in ((first, 12.508), (second, 12.52)):
        assert (
            client.put(
                "/api/v1/driver/location",
                headers=bearer(driver),
                json=location(latitude=lat),
            ).status_code
            == 200
        )
    ride = client.post(
        "/api/v1/rides",
        headers=bearer(customer),
        json={
            "pickup": "Timeout pickup",
            "dropoff": "Timeout dropoff",
            "estimated_distance_km": 2,
            "pickup_latitude": 12.508,
            "pickup_longitude": 79.884,
            "dropoff_latitude": 12.51,
            "dropoff_longitude": 79.89,
        },
    ).json()
    with Session(engine) as db:
        dispatch = db.scalar(
            select(RideDispatch).where(RideDispatch.ride_id == ride["id"])
        )
        dispatch.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(
            seconds=1
        )
        db.commit()
    assert client.get("/api/v1/driver/requests", headers=bearer(first)).json() == []
    retried = client.get("/api/v1/driver/requests", headers=bearer(second)).json()
    assert [item["id"] for item in retried] == [ride["id"]]
