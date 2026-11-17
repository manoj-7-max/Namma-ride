# Phase 1 repository verification — 16 November 2026

The selected GitHub repository was empty. A minimal README established the main branch; the full starter is proposed separately for review.

## Passed on the PR source

- Eight backend tests: liveness, pilot location/targets, private-test/demo-only mode, unauthorized admin rejection, sanitized DB failures, secret redaction and rejection of weak/example admin credentials.
- Ruff lint and formatting, Python compilation, shell syntax and Compose configuration validation.
- Random credential setup: exclusive creation, owner-only 0600 permissions and refusal to overwrite an existing .env.
- Customer Flutter: analysis without issues and three widget tests passing, including the Bike Taxi demo notice, URL validation, successful API response and server-error handling.
- Driver Flutter: analysis without issues and the same three widget tests passing.
- React/TypeScript Admin Dashboard: npm ci and production build.
- Real PostgreSQL 16: initial migration, database-backed readiness and authenticated summary, downgrade to base, re-upgrade and repeat smoke check. No customer/driver records inserted.

- Fresh backend Docker image built using the optional approved CA secret with TLS verification enabled. Full Compose API/PostgreSQL stack became healthy. Actual HTTP liveness, readiness, demo-only pilot flags, unauthorized rejection (401) and authorized zero-member summary all passed.

## Toolchain and limits

Python 3.12, Node.js 24, Flutter 3.50.0 and Dart 3.14 were available for local validation. CI uses Python 3.12, Node 22, Flutter 3.50.0 and an isolated PostgreSQL service. Remote CI results are separate from these local results.

Native Android SDK/full JDK tools from an earlier temporary build session were no longer available, so updated APKs were not built here. iOS requires macOS/Xcode. No physical device, Android emulator, browser end-to-end test or 100/10 load test was run. The installed Starlette TestClient emits a non-failing httpx deprecation warning.

Initial frontend checks hit the workspace disk limit. Obsolete prototype containers and build caches were removed; affected checks were rerun successfully. No credentials, APKs, local environment files, installed dependencies or caches are included in the commit.

## Product boundary

These are working connection/summary starters. There is no identity/onboarding, booking, dispatch, payments, public ride operation or live tracking service. Bike Taxi is demo-only. The 100-customer/10-driver numbers are pilot targets, not enforced admission limits or a capacity claim.
