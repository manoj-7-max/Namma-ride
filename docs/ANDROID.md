# Android debug APKs

Package IDs:

- Customer: `in.nammaride.namma_ride_customer.pilot`
- Driver: `in.nammaride.namma_ride_driver.pilot`

Both request internet and foreground coarse/fine location. Neither requests Android background location. Driver updates run only while the app is open and explicitly online.

## Download from GitHub Actions

1. Open the repository's **Actions** tab.
2. Select **Phase 3 Android debug APKs**.
3. Run the workflow manually, or open the successful run for the Phase 3 PR.
4. Download `namma-ride-customer-debug-apk` or `namma-ride-driver-debug-apk`.
5. Unzip the artifact and install `app-pilot-debug.apk` on the corresponding test phone. Android may require allowing installs from the browser/files app.

Artifacts are retained for 14 days. They are debug-signed, not Play Store releases, and contain no production secret or private signing key.

Set repository variable `PILOT_API_BASE_URL` to the private pilot's reachable HTTPS base URL before building. Without it, CI embeds `https://pilot-api.invalid` as an intentionally non-working safe default; users can still type a URL on the login screen.

Two physical phones require a deployed HTTPS backend reachable by both phones. An emulator-only `10.0.2.2`, USB `adb reverse`, or localhost URL does not support cross-phone tracking.

## Local build

Use Flutter 3.50.0, JDK 21, Android SDK platform/build tools 36 and NDK 28.2.13676358:

```bash
flutter build apk --debug --flavor pilot \
  --dart-define=API_BASE_URL=https://your-private-pilot.example
```

Never distribute debug APKs as production builds.
