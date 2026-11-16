# Android private-test apps

Customer package: `in.nammaride.namma_ride_customer.pilot`.
Driver package: `in.nammaride.namma_ride_driver.pilot`.

Both apps display Madurantakam, Tamil Nadu, the 100/10 pilot targets, and a Bike Taxi demo-only notice. They connect to `GET /api/v1/pilot`; booking, sign-in, dispatch, real payments and tracking are not enabled.

Use Flutter 3.50.0 stable with a full JDK 21, Android SDK platform 36, Build Tools 36.0.0 and NDK 28.2.13676358. A Java runtime without `javac` is insufficient. Run `flutter doctor`; allow at least 10 GB of free space when building apps and Docker together.

```bash
bash scripts/build-apks.sh
```

This validates both apps and produces ARM64 optimized pilot APKs at `apps/ROLE/build/app/outputs/flutter-apk/app-pilot-release.apk`. The minimum Android API is 24 (Android 7). Pilot APKs use an Android debug test key and allow local HTTP in the pilot manifest. They are not Play Store releases. Set up your own production signing identity and HTTPS configuration for any future release.

For an emulator, enter `http://10.0.2.2:8000`. For USB, use `adb reverse tcp:8000 tcp:8000` and enter `http://127.0.0.1:8000`. For a trusted LAN, follow the README's explicit API binding instructions. On a phone, localhost means that phone, not your computer. Addresses entered in the app are kept only for the current session.

The native Android toolchain was not available for a fresh APK rebuild during this repository's validation. Widget tests and analysis verify the Dart starter; they do not replace a physical-device test. iOS projects require a separate macOS/Xcode build environment.
