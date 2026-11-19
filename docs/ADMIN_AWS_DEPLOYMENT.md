# Production Admin deployment on AWS EC2

Target: `https://adminnammaride.manojbusinesssolutions.in` serving the React Admin SPA from `/var/www/namma-ride-admin/current`. Builds run on GitHub-hosted runners and call `https://api.manojbusinesssolutions.in`.

The deployment workflow does not restart or modify FastAPI, PostgreSQL or the existing API Caddy site. Do not run it until the key-rotation, DNS, CORS, directory and Caddy prerequisites below are complete.

## 1. Revoke the exposed deployment key

The earlier `namma-ride-github-actions` private key must be considered compromised. On EC2, remove every authorized key carrying its old comment:

```bash
cp "$HOME/.ssh/authorized_keys" "$HOME/.ssh/authorized_keys.before-admin-key-rotation"
sed -i '/namma-ride-github-actions/d' "$HOME/.ssh/authorized_keys"
chmod 700 "$HOME/.ssh"
chmod 600 "$HOME/.ssh/authorized_keys"
```

Generate a new dedicated key on a trusted administrator workstation where possible—not in a chat, ticket or repository:

```bash
ssh-keygen -t ed25519 -a 100 \
  -C 'namma-ride-admin-deploy-2026-11' \
  -f namma_ride_admin_deploy -N ''
```

Append only `namma_ride_admin_deploy.pub` to `/home/ubuntu/.ssh/authorized_keys`, prefixed with OpenSSH's `restrict` option to disable forwarding, agent, X11, PTY and user-rc features:

```bash
printf 'restrict %s\n' "$(cat namma_ride_admin_deploy.pub)" >> /home/ubuntu/.ssh/authorized_keys
```

Verify the key from the trusted workstation before removing local working copies:

```bash
ssh -i ./namma_ride_admin_deploy -o IdentitiesOnly=yes ubuntu@13.211.28.222 true
```

Confirm the old key is gone and exactly one new key is installed:

```bash
grep -c 'namma-ride-github-actions' "$HOME/.ssh/authorized_keys"
grep -c 'namma-ride-admin-deploy-2026-11' "$HOME/.ssh/authorized_keys"
```

Expected output is `0` and `1`. Encode the private key as one line before putting it into GitHub; base64 is transport encoding, not encryption, so the value must still be stored only as the `EC2_SSH_KEY` secret:

```bash
base64 -w0 namma_ride_admin_deploy
```

Copy the one-line output directly into the secret. The workflow tolerates whitespace and backslashes introduced by browser-terminal line wrapping, then validates the decoded OpenSSH key before connecting. Never commit it or paste it into chat. Delete the new private key from EC2 if it was temporarily created there, but retain its public key and authorized-key entry.

## 2. Configure GitHub

Create the `production-admin` GitHub Environment and optionally require approval. Add these environment or repository Actions secrets:

- `EC2_HOST`: `13.211.28.222`
- `EC2_USER`: `ubuntu`
- `EC2_SSH_KEY`: preferably the single-line base64 encoding of the complete new OpenSSH private key; raw multiline OpenSSH format is also accepted
- `EC2_SSH_HOST_KEY`: a pinned known-hosts line for the EC2 SSH host

Obtain the host key through the trusted EC2 console, not `ssh-keyscan` over an unverified network:

```bash
printf '13.211.28.222 '
sudo cat /etc/ssh/ssh_host_ed25519_key.pub
```

Join the two pieces on one line when setting `EC2_SSH_HOST_KEY`, for example `13.211.28.222 ssh-ed25519 AAAA...`. The workflow refuses unknown or mismatched host keys.

Optional Actions variable:

- `ADMIN_API_BASE_URL`: defaults to `https://api.manojbusinesssolutions.in` and must be HTTPS.

Required safety gate variable:

- `ENABLE_ADMIN_DEPLOYMENT`: leave unset or `false` while rotating keys and preparing EC2; set it to `true` only after every prerequisite and CORS check passes. The job is skipped while this gate is disabled, including immediately after the workflow is merged.

## 3. Prepare the deployment directory

Run once on EC2. This grants the deployment account access only to the Admin static tree, not Docker, Caddy configuration or application secrets:

```bash
sudo install -d -o ubuntu -g ubuntu -m 0755 /var/www/namma-ride-admin
sudo install -d -o ubuntu -g ubuntu -m 0755 /var/www/namma-ride-admin/releases
sudo touch /var/www/namma-ride-admin/.deploy.lock
sudo chown ubuntu:ubuntu /var/www/namma-ride-admin/.deploy.lock
```

Each deployment extracts into a staging directory, validates `index.html`, moves it into an immutable SHA-named release, and atomically changes the `current` symlink under an exclusive lock. Previous releases remain available for rollback. No unrelated server files are deleted.

## 4. DNS and Caddy

Create an `A` record:

```text
adminnammaride.manojbusinesssolutions.in -> 13.211.28.222
```

Inspect and back up the current configuration before changing it:

```bash
sudo cp /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.backup.$(date +%Y%m%d%H%M%S)"
sudo caddy adapt --config /etc/caddy/Caddyfile --pretty >/dev/null
```

Copy only `deploy/caddy/admin.caddy` to `/etc/caddy/sites-enabled/namma-ride-admin.caddy`. Preserve the existing `api.manojbusinesssolutions.in` block. If the main Caddyfile does not already import that directory, append only this line:

```caddyfile
import /etc/caddy/sites-enabled/*.caddy
```

Validate before the reload:

```bash
sudo caddy fmt --overwrite /etc/caddy/sites-enabled/namma-ride-admin.caddy
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl is-active caddy
```

The site configuration enables gzip/zstd, immutable hashed assets, true 404 responses for missing assets, and SPA fallback for client routes. Reloading Caddy does not restart FastAPI or PostgreSQL.

## 5. Production CORS prerequisite

The deployed API currently rejects the Admin origin until it is explicitly added. Preserve every existing origin and append:

```text
https://adminnammaride.manojbusinesssolutions.in
```

The resulting environment value is a JSON array, for example:

```dotenv
CORS_ORIGINS=["http://localhost:5173","https://adminnammaride.manojbusinesssolutions.in"]
```

Changing FastAPI environment configuration requires one controlled backend-only container recreation. Schedule this separately, back up the current environment, do not restart PostgreSQL, and verify `/health/ready` immediately afterward. The frontend deployment workflow intentionally does not modify backend configuration.

Verify CORS before the first deployment:

```bash
curl -i -X OPTIONS https://api.manojbusinesssolutions.in/api/v1/auth/admin-token \
  -H 'Origin: https://adminnammaride.manojbusinesssolutions.in' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: x-admin-key,content-type'
```

Expect HTTP 200 and `access-control-allow-origin: https://adminnammaride.manojbusinesssolutions.in`.

## 6. Deploy and validate

After merging the reviewed workflow, use GitHub Actions → **Deploy production Admin** → **Run workflow**, or push an Admin change to `main`. The job:

1. runs `npm ci` and the TypeScript/Vite build on GitHub;
2. verifies the production API configuration and uploads a 14-day artifact;
3. authenticates with the new key and pinned host key;
4. uploads to a temporary path and atomically activates a SHA release;
5. checks the home page, JS/CSS, SPA refresh, API readiness and CORS.

Independent checks:

```bash
curl -fsS https://adminnammaride.manojbusinesssolutions.in/ | grep 'Namma Ride Admin'
curl -fsS https://adminnammaride.manojbusinesssolutions.in/operations | grep 'Namma Ride Admin'
curl -fsS https://api.manojbusinesssolutions.in/health/ready
```

Do not report deployment success unless the workflow and these HTTPS checks pass.

## 7. Rollback

On EC2, inspect available releases and the current target:

```bash
readlink /var/www/namma-ride-admin/current
ls -1 /var/www/namma-ride-admin/releases
```

From `/home/ubuntu/Namma-ride`, roll back to the automatically recorded previous release:

```bash
bash scripts/rollback_admin_remote.sh
```

Or select a specific 40-character commit SHA:

```bash
bash scripts/rollback_admin_remote.sh COMMIT_SHA
```

Rollback only changes the Admin `current` symlink. It does not touch Caddy, FastAPI, Docker or PostgreSQL.
