# Android private-test apps

Customer package: `in.nammaride.namma_ride_customer.pilot`.
Driver package: `in.nammaride.namma_ride_driver.pilot`.

Both apps provide Phase 2 phone/test-OTP sign-in. Customers can request and cancel demo rides and see ride status plus assigned driver details. Drivers remain blocked until admin approval, then can reject/accept requests and advance the ride lifecycle. Payments are disabled and Bike Taxi is demo-only.

Use Flutter 3.50.0 stable with JDK 21, Android SDK platform 36, Build Tools 36.0.0 and NDK 28.2.13676358. Run:

```bash
bash scripts/build-apks.sh
```

This validates both apps and creates ARM64 pilot APKs at `apps/ROLE/build/app/outputs/flutter-apk/app-pilot-release.apk`. Minimum Android API is 24. The APKs use a debug test key, permit local HTTP only in the pilot manifest and are not Play Store releases.

For an emulator use `http://10.0.2.2:8000`. For USB, run `adb reverse tcp:8000 tcp:8000` and use `http://127.0.0.1:8000`. For trusted LAN testing follow the README's explicit binding guidance. The API address and JWT are kept only for the running app session.
