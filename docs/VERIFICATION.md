# Phase 3 verification — 17 November 2026

## Passed locally

- Backend Ruff format/lint and compilation.
- 13 backend tests covering OTP/JWT and Phase 2 lifecycle plus coordinate/accuracy/staleness validation, driver identity/role boundaries, availability, Haversine radius, nearest offer, expired-offer retry, no-driver/rematch, event authorization, assigned-driver tracking and double-accept rejection.
- Customer Flutter analysis and 2 widget tests, including integrated OTP/login/coordinate booking.
- Driver Flutter analysis and 2 widget tests, including approval gating.
- React/TypeScript Admin production build.
- Backend container source configuration and Compose configuration are covered by CI.
- A dedicated PostgreSQL concurrency smoke script uses two concurrent sessions and `FOR UPDATE` to verify exactly one assignment commits.

## APK build status

A local customer debug APK build was attempted with Flutter 3.50.0, JDK 21 and Android SDK 36. Gradle stopped because the temporary `/dev/shm` filesystem reached 100% while transforming Android dependencies. No local APK was produced, and the driver build was not started after that deterministic storage failure.

The GitHub Actions workflow has clean Ubuntu runners and is the authoritative build. An APK exists only after both workflow jobs pass and upload their named artifacts.

## CI validation

The Phase 3 PR runs:

- PostgreSQL migration upgrade, database/JWT smoke test, real row-lock concurrency test, full downgrade and re-upgrade.
- Backend tests and Ruff.
- Customer/Driver Flutter format, analysis and tests.
- Admin TypeScript/Vite build.
- Separate customer and driver debug APK builds and artifact uploads.

The non-failing Starlette TestClient compatibility warning remains. No physical-device field test, production routing, production SMS, background tracking or 100/10 concurrent load test was run.
