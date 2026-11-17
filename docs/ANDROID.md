# Android pilot APKs

Package IDs:

- Customer: `in.nammaride.namma_ride_customer.pilot`
- Driver: `in.nammaride.namma_ride_driver.pilot`

Both request internet and foreground coarse/fine location. Neither requests Android background location. Driver updates run only while the app is open and explicitly online.

## Build and download from GitHub Actions

1. Open the repository **Actions** tab.
2. Select **Android pilot release APKs**.
3. Choose **Run workflow** on the required branch.
4. Wait for both analysis/test/build jobs to pass.
5. Download `namma-ride-customer-apk` or `namma-ride-driver-apk` from the run's **Artifacts** section.
6. Unzip and install `app-pilot-release.apk`. Android may require allowing installs from the browser/files app.

Artifacts are retained for 14 days and embed `https://api.manojbusinesssolutions.in` using `--dart-define`. They contain no backend secret or private signing key.

## Signing limitation

The current Android Gradle files sign release-mode pilot APKs with Android's standard debug key. This permits private sideload testing but is not secure production signing and is not suitable for Play Store distribution. A future signing setup must use GitHub encrypted secrets and temporary runner files; no keystore, alias, or password may be committed. Changing keys also changes upgrade compatibility, so establish the pilot signing identity before broad distribution.

## Connectivity

The HTTPS readiness endpoint was reachable during repository verification, but readiness alone does not prove that the deployed server contains the merged Phase 3 schema/code. The pilot metadata endpoint reported Phase 2 at that time. Deploy and migrate the reviewed commit before testing Phase 3.

Two physical phones require the HTTPS backend to be reachable by both phones. Localhost, emulator `10.0.2.2`, and USB `adb reverse` are development-only.

## Local build

Use Flutter 3.50.0, JDK 21, Android SDK platform/build tools 36 and NDK 28.2.13676358:

```bash
flutter build apk --release --flavor pilot \
  --dart-define=API_BASE_URL=https://api.manojbusinesssolutions.in
```

Do not distribute these debug-signed APKs as public production builds.
