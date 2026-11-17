# Completion report — Phase 3 pilot hardening

Date: 17 November 2026.

## Verified implemented

- Phone/test-OTP registration and JWT customer/driver/admin roles.
- Driver approval, suspension and foreground online/offline location.
- Customer map selection, server fare calculation from submitted demo distance, booking, matching, cancellation and history.
- Nearest recent/accurate driver selection, persisted offers, timeout/rejection retry and no-driver state.
- PostgreSQL row locking and conditional assignment; concurrency smoke test.
- Requested → matching → accepted → arrived → started → completed/cancelled lifecycle.
- Authenticated SSE ride events consumed by both mobile apps with cursor reconnect; periodic polling remains fallback and discovers new driver offers.
- Assigned-driver location visibility only during active rides.
- Admin customer/driver management, approvals, suspension, rides, operations, matching failures, analytics and persisted audit entries.
- PostgreSQL migrations 0001–0004, internal-only Compose database and loopback backend binding.
- Separate manually runnable customer/driver release-mode APK workflow using the production HTTPS API.

## Hardened in this change

- OTP request rate limiting by normalized phone and time window.
- One active ride per customer.
- Immediate enforcement of customer deactivation and driver suspension on existing JWTs.
- Driver suspension marks the latest location unavailable.
- Dispatch lookup indexes.
- Configurable production CORS origins.
- Mobile SSE reconnect behavior.
- Expired/invalid JWT, management, throttling and duplicate-booking tests.

## Incomplete or deliberately limited

- OTP delivery is not integrated with an SMS provider; production must keep test OTP exposure disabled.
- Fare distance is client-supplied and ETA is straight-line estimated, not provider-routed.
- Driver offer discovery uses foreground polling; SSE covers a ride after it is visible/assigned.
- Dispatch expiry is processed by authorized polling, not a background scheduler.
- Admin provides operational location timestamps but no live map. Coordinates are deliberately not returned by the operations endpoint.
- APKs use release optimization but the Android debug signing key. Production signing is not configured.
- No push notifications, unrestricted background tracking, payments, public operation, production routing, emergency tooling, or load/field certification.
- Bike Taxi remains demo-only.

## Production verification and blocker

Read-only HTTPS checks returned:

- `GET https://api.manojbusinesssolutions.in/health/ready` → `{"status":"ready"}`
- `GET https://api.manojbusinesssolutions.in/api/v1/pilot` reported `"phase": 2`

Therefore HTTPS/Caddy and a database-backed API were reachable, but the live server was not verified as running merged Phase 3. No AWS change or deployment was made. Phase 3/0004 must be deployed and migrated under an approved operational change before end-to-end pilot testing.

End-to-end customer/driver execution against production is blocked by the missing supervised pilot accounts/OTP delivery and unverified deployed revision. Automated API integration covers the lifecycle and authorization independently.

## Private pilot launch checklist

- [ ] Review and merge the hardening PR after green CI.
- [ ] Back up PostgreSQL and rehearse restore.
- [ ] Deploy the exact reviewed commit through the existing EC2/Compose process.
- [ ] Run `alembic upgrade head` once and verify revision 0004.
- [ ] Keep PostgreSQL unpublished and port 8000 loopback/private behind Caddy.
- [ ] Configure strong unique DB/admin/JWT/OTP secrets and `EXPOSE_TEST_OTP=false`.
- [ ] Set CORS to the exact HTTPS Admin origin.
- [ ] Verify health, pilot phase, auth, SSE and logs through HTTPS.
- [ ] Establish a stable private Android signing key in encrypted CI secrets.
- [ ] Run the APK workflow and archive checksums/artifacts.
- [ ] Enroll no more than 100 customers and 10 approved drivers.
- [ ] Obtain required legal/insurance/transport approvals; keep Bike Taxi demo-only.
- [ ] Field-test permissions, GPS-off, offline/reconnect, rejection/timeout, cancellation and emergency support procedure.
- [ ] Monitor errors, matching failures, storage, certificates and backups during the supervised pilot.

