from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register(role: str, phone: str, name: str, vehicle: str | None = None):
    payload = {"phone": phone, "role": role, "display_name": name}
    if vehicle:
        payload["vehicle_number"] = vehicle
    requested = client.post("/api/v1/auth/otp/request", json=payload)
    assert requested.status_code == 200, requested.text
    challenge = requested.json()
    verified = client.post(
        "/api/v1/auth/otp/verify",
        json={
            "challenge_id": challenge["challenge_id"],
            "phone": phone,
            "otp": challenge["test_otp"],
        },
    )
    assert verified.status_code == 200, verified.text
    return verified.json()


def admin_headers():
    response = client.post(
        "/api/v1/auth/admin-token",
        headers={"X-Admin-Key": "test-admin-key-for-private-pilot-only"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def bearer(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_otp_is_one_time_and_wrong_codes_are_rejected():
    requested = client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "9876543210", "role": "customer", "display_name": "Anbu"},
    ).json()
    wrong = client.post(
        "/api/v1/auth/otp/verify",
        json={
            "challenge_id": requested["challenge_id"],
            "phone": "9876543210",
            "otp": "000000",
        },
    )
    assert wrong.status_code == 400
    good_payload = {
        "challenge_id": requested["challenge_id"],
        "phone": "9876543210",
        "otp": requested["test_otp"],
    }
    assert client.post("/api/v1/auth/otp/verify", json=good_payload).status_code == 200
    assert client.post("/api/v1/auth/otp/verify", json=good_payload).status_code == 400


def test_driver_approval_and_complete_lifecycle():
    customer = register("customer", "9876543210", "Anbu")
    driver = register("driver", "9876543211", "Selvi", "TN19AB1234")
    customer_headers, driver_headers = (
        bearer(customer["access_token"]),
        bearer(driver["access_token"]),
    )
    assert (
        client.get("/api/v1/driver/requests", headers=driver_headers).status_code == 403
    )
    approved = client.patch(
        f"/api/v1/admin/drivers/{driver['user']['id']}/approval",
        headers=admin_headers(),
        json={"approved": True},
    )
    assert approved.status_code == 200 and approved.json()["approved"] is True
    booked = client.post(
        "/api/v1/rides",
        headers=customer_headers,
        json={
            "pickup": "Madurantakam Bus Stand",
            "dropoff": "Railway Station",
            "estimated_distance_km": 4.2,
        },
    )
    assert booked.status_code == 201
    ride = booked.json()
    assert ride["status"] == "requested" and ride["estimated_fare_paise"] == 11300
    assert [
        item["id"]
        for item in client.get("/api/v1/driver/requests", headers=driver_headers).json()
    ] == [ride["id"]]
    accepted = client.post(
        f"/api/v1/driver/requests/{ride['id']}/accept", headers=driver_headers
    )
    assert (
        accepted.status_code == 200
        and accepted.json()["driver"]["display_name"] == "Selvi"
    )
    for state in ("arrived", "started", "completed"):
        response = client.patch(
            f"/api/v1/rides/{ride['id']}/status",
            headers=driver_headers,
            json={"status": state},
        )
        assert response.status_code == 200 and response.json()["status"] == state
    assert (
        client.patch(
            f"/api/v1/rides/{ride['id']}/status",
            headers=driver_headers,
            json={"status": "arrived"},
        ).status_code
        == 409
    )
    customer_view = client.get(
        f"/api/v1/rides/{ride['id']}", headers=customer_headers
    ).json()
    assert (
        customer_view["status"] == "completed"
        and customer_view["driver"]["vehicle_number"] == "TN19AB1234"
    )


def test_reject_hides_request_and_customer_can_cancel():
    customer = register("customer", "9876543212", "Kavi")
    driver = register("driver", "9876543213", "Raja", "TN19CD5678")
    driver_headers = bearer(driver["access_token"])
    client.patch(
        f"/api/v1/admin/drivers/{driver['user']['id']}/approval",
        headers=admin_headers(),
        json={"approved": True},
    )
    ride = client.post(
        "/api/v1/rides",
        headers=bearer(customer["access_token"]),
        json={
            "pickup": "Market Road",
            "dropoff": "Hospital Road",
            "estimated_distance_km": 2,
        },
    ).json()
    assert (
        client.post(
            f"/api/v1/driver/requests/{ride['id']}/reject", headers=driver_headers
        ).status_code
        == 204
    )
    assert client.get("/api/v1/driver/requests", headers=driver_headers).json() == []
    cancelled = client.patch(
        f"/api/v1/rides/{ride['id']}/status",
        headers=bearer(customer["access_token"]),
        json={"status": "cancelled", "cancellation_reason": "Plans changed"},
    )
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"


def test_role_isolation_and_admin_lists_data():
    customer = register("customer", "9876543214", "Muthu")
    assert (
        client.get(
            "/api/v1/admin/drivers", headers=bearer(customer["access_token"])
        ).status_code
        == 403
    )
    summary = client.get("/api/v1/admin/summary", headers=admin_headers())
    assert summary.status_code == 200 and summary.json()["customers"] == 1
    assert (
        client.post(
            "/api/v1/auth/admin-token", headers={"X-Admin-Key": "wrong"}
        ).status_code
        == 401
    )
