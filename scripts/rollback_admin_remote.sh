#!/usr/bin/env bash
set -Eeuo pipefail

deploy_root="${DEPLOY_ROOT:-/var/www/namma-ride-admin}"
requested="${1:-}"
if [[ -z "$requested" ]]; then
  requested="$(cat "$deploy_root/.previous" 2>/dev/null || true)"
fi
requested="${requested#releases/}"
if [[ ! "$requested" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Provide a valid release SHA or ensure .previous exists." >&2
  exit 2
fi
if [[ ! -s "$deploy_root/releases/$requested/index.html" ]]; then
  echo "Requested release is not available." >&2
  exit 3
fi

exec 9>"$deploy_root/.deploy.lock"
flock -n 9 || { echo "Another Admin deployment is in progress." >&2; exit 4; }
current="$(readlink "$deploy_root/current" 2>/dev/null || true)"
temporary_link="$deploy_root/.rollback-${requested}"
rm -f -- "$temporary_link"
ln -s "releases/$requested" "$temporary_link"
mv -Tf -- "$temporary_link" "$deploy_root/current"
if [[ "$current" =~ ^releases/[0-9a-f]{40}$ ]]; then
  printf '%s\n' "$current" > "$deploy_root/.previous"
fi
printf 'Rolled back Admin to release %s\n' "$requested"
