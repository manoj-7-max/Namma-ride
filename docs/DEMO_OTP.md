# Secure demo OTP operations

This workflow is for named Namma Ride private-pilot administrators and approved testers only. It does not enable SMS, public OTP disclosure, payments or public ride operations. The public `POST /api/v1/auth/otp/request` response never contains an OTP.

## Production configuration

Keep `EXPOSE_TEST_OTP=false`. Generate independent secrets; never reuse the normal admin key, JWT secret or OTP pepper:

```bash
openssl rand -base64 48
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store the first value as `PILOT_OTP_ADMIN_API_KEY` and the Fernet value as `PILOT_OTP_ENCRYPTION_KEY` in the server's protected environment/secret store. Do not put either value in Git, the React app, either APK, command arguments, screenshots or support messages. Apply migration `0005` before starting backend `0.3.2`. Back up PostgreSQL first; the migration is additive and does not alter existing users, rides, challenges or audit records.

The encryption key must remain available while unexpired deliveries exist. Rotating it immediately invalidates pending deliveries; request fresh codes after rotation. The dedicated administrator JWT expires after 15 minutes.

## Administrator procedure

Use a trusted administrator workstation and HTTPS. Read secrets interactively so their values do not enter shell history:

```bash
read -rsp "Pilot OTP administrator key: " PILOT_OTP_KEY; echo
API=https://api.manojbusinesssolutions.in
TOKEN=$(curl --fail --silent --show-error -X POST \
  -H "X-Pilot-Otp-Admin-Key: $PILOT_OTP_KEY" \
  "$API/api/v1/auth/pilot-otp-admin-token" | jq -r .access_token)
unset PILOT_OTP_KEY
```

Approve a tester before they request a code:

```bash
read -rp "Approved tester phone (+91...): " TESTER_PHONE
curl --fail --silent --show-error -X PUT \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data "$(jq -n --arg phone "$TESTER_PHONE" '{phone:$phone,active:true}')" \
  "$API/api/v1/admin/pilot-otp/recipients"
```

After the tester requests an OTP in an app, obtain the `challenge_id` from their screen or direct support session and retrieve it once:

```bash
read -rp "Challenge ID: " CHALLENGE_ID
curl --fail --silent --show-error -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data "$(jq -n --arg phone "$TESTER_PHONE" '{phone:$phone}')" \
  "$API/api/v1/admin/pilot-otp/challenges/$CHALLENGE_ID/retrieve"
```

Retrieval requires the exact approved phone, is one-time, sends `Cache-Control: no-store`, and fails after five minutes. The database stores only a keyed hash for verification and short-lived Fernet ciphertext for delivery. Expired ciphertext is automatically rejected and deleted during OTP request/retrieval activity. OTP values are excluded from application audit details and ordinary admin lists.

## Communicating the code

Confirm the tester's identity and last four phone digits using the pilot roster. Read the six digits over a direct voice call or use an individually addressed, end-to-end encrypted message approved for the pilot. Never use a group chat, public channel, email subject, ticket, spreadsheet, analytics field or screenshot. Do not ask the tester to send the code back. Delete any message after successful login and deactivate the recipient when their access ends:

```bash
curl --fail --silent --show-error -X PUT \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data "$(jq -n --arg phone "$TESTER_PHONE" '{phone:$phone,active:false}')" \
  "$API/api/v1/admin/pilot-otp/recipients"
unset TOKEN TESTER_PHONE CHALLENGE_ID
```

Recipient changes and successful retrievals create audit events without OTP values or phone numbers. Treat unexplained audit events as a credential incident: pause issuance, rotate the dedicated key and investigate access logs without adding request or response bodies to logs.

## Deployment and rollback

1. Back up PostgreSQL and configure both new secrets with `EXPOSE_TEST_OTP=false`.
2. Build backend dependencies, including `cryptography`.
3. Run `alembic upgrade head`; confirm revision `0005`.
4. Restart only the backend through the approved deployment process.
5. Verify readiness, approve one test number, request/retrieve/verify one code, and inspect the redacted audit entry.
6. Do not expose backend port 8000 or PostgreSQL publicly.

Rollback the application before downgrading. Migration downgrade removes pending encrypted deliveries and the recipient allowlist, so pause pilot authentication before `alembic downgrade 0004`.
