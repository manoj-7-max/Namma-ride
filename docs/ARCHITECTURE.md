# Phase 2 architecture

Flutter Customer / Flutter Driver / React Admin → FastAPI → PostgreSQL 16.

## Authentication

Customer and driver registration use normalized Indian phone numbers and a private-test OTP challenge. Challenge codes are random, HMAC-protected, expire in five minutes, are single-use and lock after five invalid attempts. `EXPOSE_TEST_OTP` controls whether the API returns the code; it defaults to false. Verified users receive short-lived JWTs with customer or driver roles. The local admin bootstrap key is exchanged for an admin JWT and is never used as ride authorization.

Drivers cannot view or accept requests until an admin approves their database record. Authenticated user records are reloaded per request, so approval revocation takes effect without waiting for JWT expiry. Enrollment is capped at 100 customers and 10 drivers.

## Ride model

Customers submit pickup, drop-off and demo distance. The server calculates the fare estimate and creates `requested`. Atomic conditional update assigns the first approved driver to accept it. Other drivers may reject a request without hiding it from colleagues.

The enforced progression is `requested → accepted → arrived → started → completed`. Cancellation is terminal and restricted by role/current state. Customer responses include assigned driver name, phone, vehicle and approval state. There is no payment or live location model.

## Persistence and configuration

Alembic owns `pilot_members`, `users`, `otp_challenges`, `rides` and `ride_rejections`. PostgreSQL constraints validate roles and ride statuses. Settings require strong database, admin, JWT and OTP secrets and redact them in representations.

Compose binds the API to loopback by default, keeps PostgreSQL internal, waits for DB health, migrates before startup and runs the API as non-root. Browser CORS defaults to the local admin origin. Bike Taxi and all fares are demo-only; public operations and payments are explicit disabled flags.
