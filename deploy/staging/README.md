# Staging: one VPS with Docker Compose, photos in Cloudflare R2

Owner: Christopher. Decided 2026-10-16 (spec decisions 3 and 4): one small Linux server running the same
stack as local (api, worker, beat, PostGIS, Redis, and the web app since 2026-10-21) plus Caddy for HTTPS;
evidence photos in Cloudflare R2.
After the one-time setup below, every merge to `main` that passes CI deploys itself
(`.github/workflows/deploy-staging.yml`).

Staging uses **test keys only** (Stripe test mode, Paystack test mode, simulated escrow): it never moves real money.

## What you need (about an hour)

| Thing | Where | Cost |
| --- | --- | --- |
| A server: Ubuntu 24.04, 2 vCPU, 4 GB RAM, 40 GB disk | Hetzner CX22, DigitalOcean, Contabo... | ~€4–12/month |
| A domain name you control, with two names on it: `api-staging.ibackhome.ng` (API) and `staging.ibackhome.ng` (web app) | your DNS provider | — |
| Cloudflare R2 bucket + API token | dash.cloudflare.com → R2 | free up to 10 GB |
| Stripe **test** secret key + webhook secret | dashboard.stripe.com (test mode) | free |
| Paystack **test** secret key | dashboard.paystack.com (test mode) | free |
| At least one way to send login codes: SMTP (e.g. Brevo free) or a Termii key | brevo.com / termii.com | free tier / pay as you go |
| Optional: Gemini API key (reports, quote checker), Sentry DSN | — | free tiers |

Without a messaging provider nobody can sign in: login codes answer 503 `notifications_not_configured`.

## 1. Create the server

1. Create the VPS with your SSH key. Note its IP.
2. DNS: add an **A record** `api-staging` → the IP (wait until `nslookup api-staging.<your domain>` shows it),
   and a second **A record** `staging` → the same IP for the web app.
3. Log in as root and run:

```bash
apt-get update && apt-get -y upgrade
# Docker Engine + Compose plugin (official convenience script)
curl -fsSL https://get.docker.com | sh
# A deploy user that can run Docker (GitHub Actions logs in as this user)
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
# Firewall: SSH and HTTPS only (Postgres and Redis are never published)
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
# The code
install -d -o deploy -g deploy /opt/ibackhome
sudo -u deploy git clone https://github.com/costechHQ/iBackHome.git /opt/ibackhome
```

## 2. Cloudflare R2

1. R2 → **Create bucket** `ibackhome-staging-evidence` (location: automatic).
2. R2 → **Manage R2 API tokens** → Create token: *Object Read & Write*, only that bucket. Copy the
   **Access Key ID**, **Secret Access Key** and the **S3 endpoint** `https://<account id>.r2.cloudflarestorage.com`.

## 3. The settings file

As `deploy` on the server:

```bash
cd /opt/ibackhome
cp deploy/staging/.env.staging.example deploy/staging/.env
chmod 600 deploy/staging/.env
nano deploy/staging/.env
```

Fill in at least: `STAGING_DOMAIN`, `STAGING_WEB_DOMAIN`, `ACME_EMAIL`, `POSTGRES_PASSWORD` and `JWT_SECRET` (`openssl rand -hex 32`),
the four `STORAGE_*` values from R2, `STRIPE_SECRET_KEY`, `PAYSTACK_SECRET_KEY`, `ESCROW_WEBHOOK_SECRET`
(`openssl rand -hex 32`), and one messaging channel (`EMAIL_SMTP_*` + `EMAIL_FROM`, or `TERMII_API_KEY`).

## 4. First start

```bash
cd /opt/ibackhome
docker compose -f deploy/staging/docker-compose.staging.yml up -d --build
docker compose -f deploy/staging/docker-compose.staging.yml ps          # all healthy after ~1 minute
curl -fsS https://$(grep ^STAGING_DOMAIN deploy/staging/.env | cut -d= -f2 | awk '{print $1}')/healthz
curl -fsS https://$(grep ^STAGING_WEB_DOMAIN deploy/staging/.env | cut -d= -f2 | awk '{print $1}')/api/healthz
```

`/healthz` answers 200 when the database, Redis and R2 are all reachable. Caddy gets the HTTPS certificate on
the first request (port 80 must be open and the DNS record must point here).

## 5. Webhooks (test mode)

| Provider | URL | Events |
| --- | --- | --- |
| Stripe (Developers → Webhooks, test mode) | `https://<STAGING_DOMAIN>/api/v1/webhooks/stripe` | `checkout.session.completed`, `checkout.session.async_payment_succeeded` |
| Paystack (Settings → API Keys & Webhooks, test mode) | `https://<STAGING_DOMAIN>/api/v1/webhooks/paystack` | (all; the app handles `transfer.*`) |

Copy Stripe's signing secret (`whsec_...`) into `STRIPE_WEBHOOK_SECRET`, then apply the change:
`docker compose -f deploy/staging/docker-compose.staging.yml up -d`.

## 6. Data and the gate

```bash
cd /opt/ibackhome
S="docker compose -f deploy/staging/docker-compose.staging.yml"
$S exec api python scripts/seed.py            # people, two Enugu projects, agents, a supplier, bank accounts
$S exec api python scripts/simulator.py       # BoQs approved, signed photos, spot checks
$S exec api pytest tests/e2e -v               # the backend gate (rolled back; outside services faked)
```

The gate test is "done when it passes on staging". Then the team does the gate review against
`https://<STAGING_DOMAIN>/docs`.

## 7. Automatic deploys

On GitHub: **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
| --- | --- |
| `STAGING_HOST` | the server's IP |
| `STAGING_USER` | `deploy` |
| `STAGING_SSH_KEY` | a new private key: `ssh-keygen -t ed25519 -N "" -f staging_deploy`; put `staging_deploy.pub` in `/home/deploy/.ssh/authorized_keys` on the server |
| `STAGING_KNOWN_HOSTS` | the output of `ssh-keyscan -t ed25519 <server IP>` |
| `STAGING_DOMAIN` | e.g. `api-staging.ibackhome.ng` |
| `STAGING_WEB_DOMAIN` | e.g. `staging.ibackhome.ng` (optional; the web health check is skipped while unset) |

From then on, each merge to `main` that passes `backend-ci` or `web-ci` (or changes `deploy/staging/`) checks out that
commit on the server, rebuilds, restarts and waits for `/healthz`. Run it by hand from Actions → deploy-staging
→ Run workflow. Until the secrets exist the workflow only prints a notice.

## Everyday

```bash
S="docker compose -f deploy/staging/docker-compose.staging.yml"
$S logs -f api worker              # JSON logs; login codes are never logged outside local
$S exec db pg_dump -U ibackhome ibackhome | gzip > ~/backup-$(date +%F).sql.gz   # a backup
$S up -d                           # after editing deploy/staging/.env (restart alone keeps the old values)
```
