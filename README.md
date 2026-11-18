# Namma Ride — Phase 3

Private-pilot platform for up to **100 customers and 10 drivers in Madurantakam, Tamil Nadu**. Phase 3 adds foreground live location, nearby-driver matching, persisted dispatch/events, customer tracking and automated pilot APK builds. **Payments and public operations remain disabled; Bike Taxi is demo-only.**

## Components

- `apps/customer`: Flutter customer app with OTP login, OpenStreetMap pickup/drop-off selection, matching, polling/reconnect and assigned-driver tracking.
- `apps/driver`: Flutter driver app with OTP login, approval gate, foreground permission flow, online/offline location, offers and navigation handoff.
- `apps/admin`: authenticated React/Vite live operations dashboard.
- `backend`: FastAPI, SQLAlchemy, PostgreSQL, SSE/polling events and Alembic migrations.
- `.github/workflows/android-apk.yml`: separate pinned customer/driver release-mode pilot APK jobs.

## Start locally

Requirements: Docker Compose v2, Python 3.11+, Node 22, Flutter 3.50.0, JDK 21 and Android SDK 36.

```bash
python3 scripts/init_env.py
docker compose up -d --build
curl http://localhost:8000/health/ready
```

The initializer creates an owner-only, Git-ignored `.env` with random secrets. `EXPOSE_TEST_OTP` must remain false; the public API never returns OTP values. Approved private-pilot testing uses the separately authorized [secure demo OTP workflow](docs/DEMO_OTP.md). API docs: `http://localhost:8000/docs`.

Matching defaults to approved, available drivers within 8 km whose latest fix is at most 120 seconds old and at most 100 m accuracy. One current fix per driver is stored—no location trail. Offers expire after 30 seconds and retry the next nearest untried driver when a customer/driver polls. All values are configurable in `.env.example`.

## Run apps

```bash
cd apps/customer # or apps/driver
flutter pub get
flutter analyze
flutter test
flutter run --flavor pilot --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

The Customer app supports map taps and current-location pickup. The Driver app shares location only after explicit foreground permission while the user is online and the app is running. Going offline stops its timer and sends an unavailable state. There is no background-location permission or hidden tracking.

For real tests across phones, the API must be deployed at a reachable **HTTPS** URL. Localhost on one phone cannot reach another phone. See [pilot setup](docs/PILOT_SETUP.md) and [Android/APK instructions](docs/ANDROID.md).

## Maps and ETA

The pilot uses `flutter_map` with OpenStreetMap raster tiles and visible attribution. No map key is embedded. Public OSM tiles are donation-funded and governed by the [tile usage policy](https://operations.osmfoundation.org/policies/tiles/); they are not an unlimited production tile service. For a larger pilot, configure a commercial/provider-hosted tile URL under its pricing and attribution terms.

No paid routing API is included. Distance remains a demo input and driver ETA is explicitly estimated from straight-line distance at 20 km/h. Do not present it as guaranteed travel time.

## Admin

```bash
cd apps/admin
npm ci
npm run dev
```

Enter the local admin bootstrap key. It is exchanged for a JWT and kept only in memory. The dashboard shows approved/online state, last fix time, active matching/rides and recent dispatch failures. It omits driver coordinates and customer phone/name from operations responses.

## Checks

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
ruff format --check app tests migrations scripts
ruff check app tests migrations scripts
pytest -q
alembic upgrade head
python scripts/check_database.py
alembic downgrade base && alembic upgrade head
```

CI runs backend/PostgreSQL, Admin and both Flutter suites. The APK workflow embeds `https://api.manojbusinesssolutions.in`, runs mobile checks, and builds release-mode pilot APK artifacts. Until private signing is configured, Gradle deliberately uses the standard debug key; these are not Play Store or production-signed releases. See [architecture](docs/ARCHITECTURE.md), [phases](docs/PHASES.md), [secure demo OTP operations](docs/DEMO_OTP.md), [completion report](docs/COMPLETION_REPORT.md) and [verification](docs/VERIFICATION.md).

## Security boundary

The API derives driver identity from JWTs, validates coordinates/time/accuracy, rate-limits fixes, reloads approval state, restricts tracking to the assigned customer during active rides and uses PostgreSQL row locks for acceptance. Ride events persist state changes, not a location trail. SSE uses bearer authentication; mobile polling is the fallback.

This is not production dispatch software: no production SMS, push notifications, turn-by-turn routing, background tracking, payments, public operation, production signing, emergency flow or legal compliance certification is included.
