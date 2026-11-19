#!/usr/bin/env bash
set -Eeuo pipefail
umask 022

release_id="${1:-}"
archive="${2:-}"
deploy_root="${DEPLOY_ROOT:-/var/www/namma-ride-admin}"
releases_root="$deploy_root/releases"

if [[ ! "$release_id" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Release ID must be a 40-character Git commit SHA." >&2
  exit 2
fi
expected_archive="/tmp/namma-ride-admin-${release_id}.tar.gz"
if [[ "$archive" != "$expected_archive" || ! -f "$archive" ]]; then
  echo "Expected deployment archive is unavailable." >&2
  exit 2
fi
if [[ ! -d "$releases_root" || ! -w "$releases_root" ]]; then
  echo "$releases_root must exist and be writable by the deployment user." >&2
  exit 3
fi

exec 9>"$deploy_root/.deploy.lock"
if ! flock -n 9; then
  echo "Another Admin deployment is in progress." >&2
  exit 4
fi

staging="$releases_root/.${release_id}.staging"
release="$releases_root/$release_id"
cleanup() {
  rm -f -- "$archive"
  rm -rf -- "$staging"
}
trap cleanup EXIT

if [[ ! -d "$release" ]]; then
  rm -rf -- "$staging"
  mkdir -m 755 "$staging"
  tar -xzf "$archive" --no-same-owner --no-same-permissions -C "$staging"
  if find "$staging" -type l -print -quit | grep -q .; then
    echo "Deployment archives must not contain symbolic links." >&2
    exit 5
  fi
  test -s "$staging/index.html"
  grep -Fq 'Namma Ride Admin' "$staging/index.html"
  find "$staging" -type d -exec chmod 755 {} +
  find "$staging" -type f -exec chmod 644 {} +
  mv -- "$staging" "$release"
fi

previous="$(readlink "$deploy_root/current" 2>/dev/null || true)"
if [[ -n "$previous" && "$previous" =~ ^releases/[0-9a-f]{40}$ ]]; then
  printf '%s\n' "$previous" > "$deploy_root/.previous"
fi
temporary_link="$deploy_root/.current-${release_id}"
rm -f -- "$temporary_link"
ln -s "releases/$release_id" "$temporary_link"
mv -Tf -- "$temporary_link" "$deploy_root/current"
test -s "$deploy_root/current/index.html"
printf 'Activated Admin release %s\n' "$release_id"
