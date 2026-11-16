# Phase 1 architecture

Flutter Customer / Flutter Driver / React Admin → FastAPI → PostgreSQL 16.

## API

| Route | Access | Purpose |
| --- | --- | --- |
| `GET /health/live` | Public metadata | Process liveness |
| `GET /health/ready` | Public metadata | DB connectivity and migrated table availability |
| `GET /api/v1/pilot` | Public metadata | Madurantakam, Tamil Nadu; private-test mode; 100/10 targets; disabled real payments and public operations; demo-only Bike Taxi |
| `GET /api/v1/admin/summary` | `X-Admin-Key` | Actual DB member counts and pilot targets |

No route creates bookings, enrolls members, dispatches drivers, processes payments or starts public operations. The mode flags are explicit constants for this foundation. Mobile clients never receive admin credentials.

## Persistence and configuration

Alembic owns the `pilot_members` schema: integer ID, constrained customer/driver role, display name and timestamp. The initial database is empty. Registration limits, identity, driver verification and rides belong to later phases.

Settings require random database/admin credentials, reject placeholder secrets and redact secret fields in their representations. Connection URLs escape credential components. DB failure responses return sanitized 503 errors. Admin comparison uses constant-time comparison. The admin key is only a local private-test mechanism, not a full authentication system.

Compose binds the API to loopback by default, does not publish PostgreSQL, waits for DB health and runs the API without root privileges. The persistent named volume survives container shutdown. Browser CORS defaults to http://localhost:5173; add only explicit development origins as needed. A LAN binding is an intentional local testing option, not public deployment.
