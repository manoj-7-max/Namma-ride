from app.config import get_settings


def pilot_otp_headers(client):
    response = client.post(
        "/api/v1/auth/pilot-otp-admin-token",
        headers={
            "X-Pilot-Otp-Admin-Key": get_settings().pilot_otp_admin_api_key.get_secret_value()
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def request_pilot_otp(client, payload):
    headers = pilot_otp_headers(client)
    approved = client.put(
        "/api/v1/admin/pilot-otp/recipients",
        headers=headers,
        json={"phone": payload["phone"], "active": True},
    )
    assert approved.status_code == 200, approved.text
    requested = client.post("/api/v1/auth/otp/request", json=payload)
    assert requested.status_code == 200, requested.text
    challenge = requested.json()
    assert "otp" not in challenge and "test_otp" not in challenge
    retrieved = client.post(
        f"/api/v1/admin/pilot-otp/challenges/{challenge['challenge_id']}/retrieve",
        headers=headers,
        json={"phone": payload["phone"]},
    )
    assert retrieved.status_code == 200, retrieved.text
    return challenge, retrieved.json()["otp"]
