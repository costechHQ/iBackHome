# Production: a second Contabo server, same stack as staging, real money OFF

Owner: Christopher. Plan: `Docs/iBackHome-60-Day-Plan-and-Production-Cutover.pdf` (section 5, Route A).
Staging stays as it is. Production is a **new server beside it**, with its own database, its own R2 bucket and its
own secrets. Anything here that says "as in staging" means the matching part of `Docs/ibackhome-contabo-deployment-guide.pdf`.

Addresses (domain `ibackhome.com`; change it everywhere if yours differs):

| Name | What |
| --- | --- |
| `ibackhome.com` and `www.ibackhome.com` | the web app (`www` redirects to the root) |
| `api.ibackhome.com` | the API (`/healthz`, `/docs`, webhooks, the mobile app) |

## Rules for this first release

1. **Real money is off.** Stripe and Paystack keep their **test** keys; escrow is `simulated` (no partner has signed).
   Users must be told it is a pilot. Switching to live keys is a separate, later decision.
2. **Deploy by hand** (`git pull` + `up -d --build`). There is no auto-deploy for production.
3. **Never run `scripts/seed.py` or `simulator.py`**: seed refuses `ENVIRONMENT=production` on purpose. No demo data.
4. **Secrets are new**: do not copy staging's `.env`. Generate fresh ones (step 6).
5. `IBH_MOCKS` is not set in the production compose file, so the web app shows no sample data.

## 0. Value sheet (keep in a password manager, never in git)

Server IP · deploy user · `POSTGRES_PASSWORD` · `JWT_SECRET` · `NIN_ENCRYPTION_KEY` (**keep an offline copy: if lost,
pending NINs cannot be read**) · `ESCROW_WEBHOOK_SECRET` · R2 account id / access key / secret key · Stripe test keys ·
Paystack test key · email provider login · Sentry DSN.

## 1. Order the server (Contabo, click-through)

1. Go to **contabo.com** → **Log in** (Customer Control Panel) → **Order** (or the shop: **Cloud VPS**).
2. Pick **Cloud VPS 10 or bigger** (the web build needs memory; 4 GB RAM minimum, 8 GB is safer), region of your
   choice (EU is fine), **Storage 150 GB SSD** default.
3. **Image**: Ubuntu 24.04. **Login**: choose **SSH key** and paste your **public** key (`~/.ssh/id_ed25519.pub`;
   create one with `ssh-keygen -t ed25519` in Git Bash if you have none). Do not use a password login.
4. No add-ons needed. **Pay**. Contabo emails the IP when ready (a few minutes to an hour).
5. Write the IP in the value sheet. Test: `ssh root@<IP>` from Git Bash.

## 2. Server preparation (as root)

```bash
apt-get update && apt-get -y upgrade
# 4 GB swap (stops the web build running out of memory)
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
# Docker Engine + Compose plugin
curl -fsSL https://get.docker.com | sh
# the deploy user
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
chown deploy:deploy /home/deploy/.ssh/authorized_keys && chmod 600 /home/deploy/.ssh/authorized_keys
# firewall: SSH, HTTP, HTTPS only
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
install -d -o deploy -g deploy /opt/ibackhome
```

Open a **second** terminal and check `ssh deploy@<IP>` works **before** closing the root one. Then harden SSH (step 11).

## 3. DNS (your DNS provider's dashboard)

Add three **A records** pointing at the server IP:

| Type | Name | Value |
| --- | --- | --- |
| A | `@` (root) | server IP |
| A | `www` | server IP |
| A | `api` | server IP |

- Cloudflare DNS: set each to **DNS only** (grey cloud), not Proxied, or Caddy cannot get certificates.
- Set the TTL to 5 minutes (300 s) while cutting over; raise it to 1 hour afterwards.
- Wait until `nslookup api.ibackhome.com` shows the new IP. Only then go to step 7 (Caddy needs the records to get HTTPS).
- If the root domain currently serves anything else (a parked page), it is replaced when you add the record.

## 4. Let the server read the repository

Same as staging (guide Part 8): a read-only **deploy key**.

On the server as `deploy`:

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/ibackhome_repo
cat ~/.ssh/ibackhome_repo.pub        # copy this line
printf 'Host github.com\n  IdentityFile ~/.ssh/ibackhome_repo\n  IdentitiesOnly yes\n' >> ~/.ssh/config
chmod 600 ~/.ssh/config
```

On GitHub: repo **costechHQ/iBackHome → Settings → Deploy keys → Add deploy key**; title `production server`; paste the
line; leave **Allow write access unticked**; **Add key**. Then on the server:

```bash
ssh-keyscan -t ed25519 github.com >> ~/.ssh/known_hosts
git clone git@github.com:costechHQ/iBackHome.git /opt/ibackhome
cd /opt/ibackhome && git log --oneline -1
```

(A deploy key can only be used on one repository and one server at a time: this one is separate from staging's.)

## 5. Cloudflare R2 (photos), a separate bucket

1. dash.cloudflare.com → **R2 Object Storage** → **Create bucket** → name `ibackhome-production-evidence`, location
   Automatic → **Create**.
2. R2 overview → **Manage R2 API Tokens** (right side) → **Create API token** → permission **Object Read & Write** →
   **Specify bucket(s)**: only `ibackhome-production-evidence` → **Create API Token**.
3. Copy **Access Key ID**, **Secret Access Key** and the endpoint `https://<account id>.r2.cloudflarestorage.com`
   (shown once: save it now). The bucket stays **private**.

## 6. Keys for the settings file

- **Email for login codes** (nobody can sign in without a channel). Brevo: brevo.com → **SMTP & API → SMTP** →
  **Generate a new SMTP key**; note login and key. Then **Senders, Domains & Dedicated IPs → Domains → Add a domain**
  `ibackhome.com`, and add the SPF/DKIM/DMARC records it shows at your DNS provider (slow: start early). `EMAIL_FROM`
  must use that domain, otherwise codes land in spam.
- **Stripe** (dashboard.stripe.com, switch to **Test mode**): **Developers → API keys → Secret key** (`sk_test_...`).
  The webhook comes in step 9.
- **Paystack** (dashboard.paystack.com, **Test mode** toggle): **Settings → API Keys & Webhooks → Test Secret Key**.
- Optional: Gemini key (`LLM_API_KEY`), Sentry project DSN (sentry.io → **Projects → Create Project → Python/FastAPI**).
- Generate secrets on the server:

```bash
openssl rand -hex 24   # POSTGRES_PASSWORD
openssl rand -hex 32   # JWT_SECRET
openssl rand -hex 32   # NIN_ENCRYPTION_KEY  (offline copy!)
openssl rand -hex 32   # ESCROW_WEBHOOK_SECRET
```

## 7. The settings file

As `deploy` on the server:

```bash
cd /opt/ibackhome
cp deploy/production/.env.production.example deploy/production/.env
chmod 600 deploy/production/.env
nano deploy/production/.env       # Ctrl+O Enter to save, Ctrl+X to exit
```

Fill in: `API_DOMAIN=api.ibackhome.com`, `WEB_DOMAIN=ibackhome.com`, `ACME_EMAIL`, `POSTGRES_PASSWORD`, `JWT_SECRET`,
`NIN_ENCRYPTION_KEY`, the four `STORAGE_*` values (bucket `ibackhome-production-evidence`), `STRIPE_SECRET_KEY` and
`PAYSTACK_SECRET_KEY` (**test** keys), `ESCROW_WEBHOOK_SECRET`, the `EMAIL_SMTP_*` + `EMAIL_FROM` block, and replace
`<WEB_DOMAIN>` in the two `FUNDING_*_URL` lines with `ibackhome.com`. Leave `STRIPE_WEBHOOK_SECRET` empty until step 9.
Check: no line may still say `staging`, and `grep -c '^ESCROW_PROVIDER' deploy/production/.env` should be 0 (simulated is the default).

## 8. First start

```bash
cd /opt/ibackhome
P="docker compose -f deploy/production/docker-compose.production.yml"
$P up -d --build        # the first build takes 5-15 minutes
$P ps                   # api, db, redis, web healthy after ~1-2 minutes
curl -fsS https://api.ibackhome.com/healthz        # 200: database, Redis and storage all reachable
curl -fsS https://ibackhome.com/api/healthz
```

Browser check: `https://ibackhome.com` loads with a padlock; `https://www.ibackhome.com` redirects to it.
The API runs the migrations itself on start. If something fails: `$P logs --tail=100 api` (or `web`, `caddy`).

## 9. Stripe webhook (test mode)

Stripe dashboard (Test mode) → **Developers → Webhooks → Add endpoint** → URL
`https://api.ibackhome.com/api/v1/webhooks/stripe` → events `checkout.session.completed` and
`checkout.session.async_payment_succeeded` → **Add endpoint** → **Reveal signing secret** (`whsec_...`). Put it in
`STRIPE_WEBHOOK_SECRET` in `deploy/production/.env`, then `$P up -d` (restart alone keeps the old value).
Paystack: Settings → API Keys & Webhooks → **Test Webhook URL** `https://api.ibackhome.com/api/v1/webhooks/paystack`.

## 10. The first ops account (no seed data)

1. Open `https://ibackhome.com`, sign in with your email: a code arrives from the production domain (this is go-live
   condition 1). You are created as a `client`.
2. Promote yourself to ops (the only database edit; there is no route for it, by design):

```bash
$P exec db psql -U ibackhome ibackhome -c "UPDATE users SET role='ops' WHERE email='you@yourdomain.com' RETURNING id,email,role;"
```

   Replace the email with yours. Sign out and in again so the new role is in your token. A second ops person is needed
   to resolve disputes (two different ops users): repeat for them.
3. Load the milestone checklists once Lilian has the final wording (`scripts/load_checklists.py`, see its header).

## 11. Prove it (go-live conditions, all five must be true)

```bash
$P exec api pytest tests/e2e -v       # the gate test; rolls back, safe, creates nothing
```

| Condition | Check |
| --- | --- |
| Login codes arrive from the production domain | step 10 |
| A backup has been restored | step 12 |
| Mocks off, no placeholder secret | the app refuses to start with a placeholder `JWT_SECRET`; `grep MOCKS deploy/production/docker-compose.production.yml` prints nothing |
| Gate test passes on this server | the pytest above |
| Real money off and users can tell it is a pilot | test keys + simulated escrow; the web "pilot, no real money yet" notice still needs a small web change (propose it first) |

Also: walk through sign-up → create project → set site → ops console by hand; turn on Sentry and an uptime monitor
(UptimeRobot: **Add New Monitor → HTTP(s)** on `https://api.ibackhome.com/healthz`, 5-minute interval).

## 12. Backups (before anyone uses it)

```bash
mkdir -p ~/backups
crontab -e        # choose nano, add this line, save:
# 0 2 * * * cd /opt/ibackhome && docker compose -f deploy/production/docker-compose.production.yml exec -T db pg_dump -U ibackhome ibackhome | gzip > ~/backups/db-$(date +\%F).sql.gz && find ~/backups -mtime +14 -delete
```

Run the command once by hand, then **test the restore** into a scratch database:

```bash
$P exec -T db psql -U ibackhome -c "CREATE DATABASE scratch;"
gunzip -c ~/backups/db-$(date +%F).sql.gz | $P exec -T db psql -U ibackhome scratch -q
$P exec db psql -U ibackhome scratch -c "SELECT count(*) FROM users;"
$P exec -T db psql -U ibackhome -c "DROP DATABASE scratch;"
```

Copy one backup off the server (from your PC, Git Bash): `scp deploy@<IP>:backups/db-<date>.sql.gz .`
R2 holds the photos (not backed up by this); keep the `NIN_ENCRYPTION_KEY` copy offline.

SSH hardening (after confirming `ssh deploy@<IP>` works): `sudo nano /etc/ssh/sshd_config`, set `PermitRootLogin no` and
`PasswordAuthentication no`, then `sudo systemctl restart ssh`. Check `sudo ufw status` shows only 22, 80, 443.

## 13. Releasing a new version (by hand)

```bash
cd /opt/ibackhome && git fetch origin main
git rev-parse --short HEAD > ~/previous-release      # rollback point
git checkout --detach origin/main
$P up -d --build --remove-orphans && curl -fsS https://api.ibackhome.com/healthz
```

**Rollback:** `git checkout --detach $(cat ~/previous-release) && $P up -d --build`. Migrations only go forward; if a
release added one, restore the pre-release backup rather than downgrading (take a manual `pg_dump` before each release).
**DNS rollback:** staging is untouched; point the records back if the new server must be abandoned.

## Later (not in this release)

Live Stripe/Paystack keys (new webhook endpoints with live secrets), a signed escrow partner (`ESCROW_PROVIDER` only
accepts `simulated` today), WhatsApp templates and `WHATSAPP_USE_TEMPLATES=true`, Firebase push, an automatic deploy workflow.

## Everyday

```bash
$P logs -f api worker              # JSON logs
$P up -d                           # after editing deploy/production/.env
$P ps
```
