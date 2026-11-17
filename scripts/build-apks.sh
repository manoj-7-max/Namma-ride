#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v flutter >/dev/null || { echo 'Install Flutter stable and Android SDK first.'; exit 1; }
for role in customer driver; do
  (
    cd "apps/$role"
    flutter pub get
    flutter analyze
    flutter test
    flutter build apk --release --flavor pilot --target-platform android-arm64
  )
done
# Test builds use Android debug signing; do not upload them to Google Play.
