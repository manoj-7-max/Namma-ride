# Phase 3 verification — 17 November 2026

## Passed locally

- Backend Ruff format/lint and compilation.
- 17 backend tests covering OTP/JWT throttling and expiry, account suspension, duplicate active-booking prevention, Phase 2 lifecycle, coordinate/accuracy/staleness validation, driver identity/role boundaries, availability, Haversine radius, nearest offer, expired-offer retry, no-driver/rematch, event authorization, assigned-driver tracking and double-accept rejection.
- Customer Flutter analysis and 2 widget tests, including integrated OTP/login/coordinate booking.
- Driver Flutter analysis and 2 widget tests, including approval gating.
- React/TypeScript Admin production build.
- Backend container source configuration and Compose configuration are covered by CI.
- A dedicated PostgreSQL concurrency smoke script uses two concurrent sessions and `FOR UPDATE` to verify exactly one assignment commits.

## APK build status

GitHub Actions run [44131107468](https://github.com/manoj-7-max/Namma-ride/actions/runs/44131107468) passed on 17 November 2026. Both jobs ran format checks, Flutter analysis and tests before building release-mode pilot APKs with `API_BASE_URL=https://api.manojbusinesssolutions.in`.

- `namma-ride-customer-apk`: uploaded successfully; retained until 1 December 2026.
- `namma-ride-driver-apk`: uploaded successfully; retained until 1 December 2026.

These private-pilot APKs are release optimized but use Android's debug signing key. They are suitable for sideload testing only, are not Play Store release artifacts, and contain no private signing credentials. The installed apps still require a reachable, compatible HTTPS backend. The production health endpoint was reachable during this verification, but `/api/v1/pilot` reported Phase 2, so compatibility with this branch is not yet established.

## CI validation

The Phase 3 PR runs:

- PostgreSQL migration upgrade, database/JWT smoke test, real row-lock concurrency test, full downgrade and re-upgrade.
- Backend tests and Ruff.
- Customer/Driver Flutter format, analysis and tests.
- Admin TypeScript/Vite build.
- Separate customer and driver release-mode pilot APK builds and artifact uploads.

All PR checks passed. The non-failing Starlette TestClient compatibility warning and GitHub's third-party action Node-version notices remain. No physical-device end-to-end field test, production routing, production SMS, unrestricted background tracking or 100/10 concurrent load test was run.
