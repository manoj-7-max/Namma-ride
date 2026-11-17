# Namma Ride — Phase 2

Private-test MVP for up to **100 customers and 10 drivers in Madurantakam, Tamil Nadu**. It provides phone/test-OTP authentication, role-scoped JWTs, driver approval, demo ride booking and the complete ride lifecycle. **Payments remain disabled, public ride operations are disabled, and Bike Taxi is demo-only.**

## Repository

| Path | Purpose |
| --- | --- |
| `apps/customer` | Flutter Customer Android app: OTP login, booking and ride status |
| `apps/driver` | Flutter Driver Android app: approval gate, requests and lifecycle actions |
| `apps/admin` | React + TypeScript + Vite driver/ride dashboard |
| `backend/app` | FastAPI, JWT auth, SQLAlchemy models and APIs |
| `backend/migrations` | Alembic schema migrations |
| `backend/tests` | Authentication, authorization and ride-flow tests |
| `docker-compose.yml` | Local PostgreSQL 16 and API services |

## Requirements

- Docker Engine with Compose v2
- Python 3.11+ (tested with 3.12)
- Node.js 22 and npm
- Flutter 3.50.0 stable / Dart 3.14
- JDK 21 and Android SDK platform/build tools 36 for APK builds

## Start the API and PostgreSQL

```bash
python3 scripts/init_env.py
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health/ready
```

`init_env.py` creates a Git-ignored, owner-only `.env` containing random database, admin, JWT and OTP secrets. It never overwrites an existing file. Placeholder or short secrets are rejected. PostgreSQL is not published to the host; the API binds to loopback by default and runs migrations before startup.

For local test OTPs only, change `EXPOSE_TEST_OTP=false` to `true` in `.env`, then recreate the API with `docker compose up -d --force-recreate api`. The OTP is returned by the request endpoint and displayed by the apps. Keep this setting false outside a controlled test environment. OTPs are randomly generated, HMAC-protected at rest, expire after five minutes, permit five attempts and are single-use. This repository does not send SMS.

API docs are at **http://localhost:8000/docs**. The standard flow is:

1. `POST /api/v1/auth/otp/request`, then `POST /api/v1/auth/otp/verify`.
2. Send the returned JWT as `Authorization: Bearer TOKEN`.
3. Customers create rides with `POST /api/v1/rides`.
4. An admin approves registered drivers.
5. Approved drivers accept or reject requests, then advance Accepted → Arrived → Started → Completed.

Customers may cancel requested or accepted rides. Assigned drivers may cancel accepted or arrived rides; admins may cancel active rides. Estimated fares are demo estimates only: ₹50 base plus ₹15/km. There is no payment collection.

## Run the Admin Dashboard

```bash
cd apps/admin
cp .env.example .env
npm ci
npm run dev
```

Open **http://localhost:5173** and enter `ADMIN_API_KEY` from the root `.env`. The key is exchanged for a short-lived admin JWT and retained only in component memory. The dashboard shows pilot counts, approves/revokes drivers, lists rides and can cancel active rides. Never put credentials in a `VITE_*` variable.

## Run the Flutter apps

```bash
cd apps/customer  # or apps/driver
flutter pub get
flutter analyze
flutter test
flutter run --flavor pilot
```

Enter the API base URL on the login screen:

- Android emulator: `http://10.0.2.2:8000`
- USB device: run `adb reverse tcp:8000 tcp:8000`, then use `http://127.0.0.1:8000`
- Trusted LAN: deliberately bind the API to `0.0.0.0`, restrict the host firewall and use the computer's LAN address

The pilot flavor permits local HTTP and has a `.pilot` application ID suffix. A remote test needs a private, reachable HTTPS API. See [Android setup](docs/ANDROID.md).

## Development checks

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
ruff format --check app tests migrations scripts
ruff check app tests migrations scripts
pytest -q
alembic upgrade head
python scripts/check_database.py
```

```bash
cd apps/admin && npm ci && npm run build
cd apps/customer && flutter pub get && flutter analyze && flutter test
cd apps/driver && flutter pub get && flutter analyze && flutter test
```

CI also upgrades, fully rolls back and reapplies the PostgreSQL migrations. Build private pilot APKs with `bash scripts/build-apks.sh`; they use a debug test key and are not store releases.

## Security and pilot boundaries

JWTs use HS256 with an issuer, expiry and role claim. The API reloads each customer/driver from the database on authenticated requests, so revoked driver approval is effective immediately. Role checks protect every ride/admin operation; atomic acceptance prevents two drivers claiming the same request. Admission is capped at 100 customer and 10 driver records.

This remains test software: no SMS provider, live GPS, maps/routing, background notifications, payment processing, public deployment, production signing, audit log or backup automation is included. Distance is customer-entered for the demo fare and service-area enforcement is not yet geographic. Do not use it for public transport operations.

See [architecture](docs/ARCHITECTURE.md), [phase boundaries](docs/PHASES.md) and [verification](docs/VERIFICATION.md).
