# Namma Ride — Phase 1

Working private-test starter for **100 customers and 10 drivers in Madurantakam, Tamil Nadu**. **No public ride operations or real payment processing. Bike Taxi is demo-only.**

Phase 1 connects Customer and Driver apps to pilot metadata and provides an authenticated admin summary backed by PostgreSQL. Enrollment, ride booking, matching, live tracking and payments are not implemented. The 100/10 figures are pilot targets, not enforced registration limits or verified load capacity.

## Repository

| Path | Purpose |
| --- | --- |
| `apps/customer` | Flutter Customer App with Android, iOS and web projects |
| `apps/driver` | Flutter Driver App with Android, iOS and web projects |
| `apps/admin` | React + TypeScript + Vite Admin Dashboard |
| `backend/app` | FastAPI settings, endpoints and SQLAlchemy model |
| `backend/migrations` | Alembic PostgreSQL schema migration |
| `backend/tests` | API behavior and secret configuration tests |
| `docker-compose.yml` | Local PostgreSQL 16 and API services |
| `.github/workflows/checks.yml` | Backend/PostgreSQL, admin and Flutter checks |

## Requirements

- Docker Engine with Compose v2 for the API/database stack.
- Python 3.11+ (tested with 3.12) for development and local-secret generation.
- Node.js 22 and npm for the dashboard.
- Flutter **3.50.0 stable** / Dart 3.14 for the mobile apps and widget tests.
- A full JDK 21, Android SDK and a device/emulator for Android runs. iOS requires macOS and Xcode. Run `flutter doctor` for platform-specific dependencies.

## 1. Start the backend and database

From the repository root:

```bash
python3 scripts/init_env.py
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health/ready
curl http://localhost:8000/api/v1/pilot
```

The initializer creates a Git-ignored `.env` with random database and admin secrets, owner-only file permissions and loopback API binding. It refuses to overwrite an existing `.env`. `.env.example` documents the variables; placeholder and short secrets are rejected by the API. Never commit local credentials. If you already have `.env`, keep its credentials consistent with the existing database volume.

The backend runs migrations before Uvicorn, runs as a non-root user and listens at **http://localhost:8000**. Interactive API docs: **http://localhost:8000/docs**. PostgreSQL has no host port mapping. `docker compose down` preserves the database; `down -v` deletes it.

## 2. Run the Admin Dashboard

In another terminal:

```bash
cd apps/admin
cp .env.example .env
npm ci
npm run dev
```

Open **http://localhost:5173** and enter `ADMIN_API_KEY` from your root `.env`. The dashboard sends it as `X-Admin-Key` and keeps it only in component memory. Do not put secrets in `VITE_*` variables. Counts start at zero; no member creation endpoint is exposed in Phase 1.

## 3. Run Customer and Driver apps

Repeat for each app, with an Android device/emulator available:

```bash
cd apps/customer  # use apps/driver for the Driver App
flutter pub get
flutter analyze
flutter test
flutter run --flavor pilot
```

Enter the API base URL in the app and tap **Check API connection**. The apps display Madurantakam pilot information and an explicit demo-only Bike Taxi notice. API addresses are retained only for the current session.

- Android emulator: `http://10.0.2.2:8000`.
- USB-connected device: run `adb reverse tcp:8000 tcp:8000`, then enter `http://127.0.0.1:8000`.
- Trusted Wi-Fi: deliberately set root `API_BIND_HOST=0.0.0.0`, recreate the backend, allow port 8000 on the host and enter `http://COMPUTER_LAN_IP:8000`.
- Hosted/private remote testing needs a reachable HTTPS backend; none is provisioned by this repository.

The pilot flavor allows local HTTP and uses a `.pilot` application ID suffix. The base manifest keeps Android's secure transport defaults. This project does not enable public operations. See [Android setup](docs/ANDROID.md). Flutter web needs an explicit allowed origin in the backend's JSON `CORS_ORIGINS` setting; the default allows only the admin origin.

## Checks

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
ruff check app tests migrations scripts
```

```bash
cd apps/admin
npm ci
npm run build
```

For each Flutter app, run `flutter pub get`, `flutter analyze` and `flutter test`. CI runs those checks and also applies/rolls back the migration against an isolated PostgreSQL service. For an optional Android pilot APK build, run `bash scripts/build-apks.sh` from the root; pilot builds use a debug test key and are not for store submission.

For host-based backend development, `backend/.env.example` lists the DB settings. Set matching credentials, make your test database reachable, run `alembic upgrade head`, then `uvicorn app.main:app --reload` from `backend/`. Compose's database is internal-only by default; do not assume it is reachable on the host's port 5432.

## Proxy certificate support

If your network intercepts TLS, mount an approved combined CA bundle as a temporary build secret:

```bash
docker build --secret id=build_ca,src=/path/to/approved-ca-bundle.pem -t namma-ride-backend backend
docker compose up -d --no-build
```

The bundle is not copied into image layers. Keep TLS verification enabled. Other networks can use the normal Compose build.

See [verification results](docs/VERIFICATION.md), [architecture](docs/ARCHITECTURE.md) and [phase boundaries](docs/PHASES.md). Before inviting testers, implement invite-only identities, individual admin roles, enrollment caps, service-area validation, consent, audit records and backup/restore procedures. Phase 1 stores no real rider or driver data by default.
