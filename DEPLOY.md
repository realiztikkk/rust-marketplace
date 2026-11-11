# Deploy — The Rusting Dead Mod Marketplace (OVH)

How to get the marketplace live on `plugins.therustingdead.com` so we can
test and improve it iteratively. Target: the OVH game-server box
(`51.222.245.218`, user `rustserver`, Ubuntu 22.04.5) — the box that runs
The Rusting Dead server. The home machine (`zmedia`) is NOT the deploy
target and needs no access for this.

## What is already ready

- `Dockerfile` — Python 3.12-slim, non-root, healthcheck on `/health`,
  ships `app/` + `brand/` (logo + banner).
- `docker-compose.yml` — one service, port `8000`, volume `./data:/data`
  (SQLite DB + uploaded plugin files). All state lives in `./data`;
  back that folder up and you have everything.
- `docker-compose.ovh.yml` + `Caddyfile` — adds a Caddy reverse proxy
  with automatic HTTPS for `plugins.therustingdead.com`.
- `.env.example` — every setting, with PayPal sandbox first.
- `PAYPAL-SETUP.md` — the PayPal sandbox walkthrough (separate step,
  after the site is up).
- `POLICY-DRAFT.md` — review / refund / chargeback policies drafted
  from RogueDepot (still to be adopted as written).
- Code is in GitHub: `realiztikkk/rust-marketplace` (private, main).
  Every change goes through that repo — pulls included.

## Access needed (one time)

1. **SSH key** — my public key goes in `rustserver`'s
   `~/.ssh/authorized_keys` on the OVH box (my own key, not Eugene's):
   `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEIZ9FfcwKFuKYuFtJN4bXIBwvnvxeZsJWg7qtqxF+lL hatch`
2. **How I reach the box** — outbound SSH from this VM is off, so I
   reach it through the Tailscale tunnel proxy *if the OVH box is on
   your Tailscale network*. If it is not, the box needs to join the
   tailnet (or outbound SSH needs enabling). The home-machine Tailscale
   approval is NOT needed for this deploy.
3. **Docker on the box** — install status unknown; check with
   `docker --version`. If it is not installed, install Docker Engine
   + the Compose plugin and add `rustserver` to the `docker` group.

## Step 1 — DNS (Dynu)

Add an `A` record in Dynu (a specific record beats the wildcard):

- Host: `plugins`
- Domain: `therustingdead.com`
- Value: `51.222.245.218`

Do this BEFORE the first Caddy run, or Caddy cannot get its
certificate.

## Step 2 — On the OVH box

```bash
# Next to the game server data
cd /data1
git clone https://github.com/realiztikkk/rust-marketplace.git marketplace
cd marketplace

# Brand images travel separately (the GitHub connector cannot push
# binary files): copy brand/ from the workspace to the box, e.g.
#   scp -r brand/ rustserver@51.222.245.218:/data1/marketplace/brand/
# (or any other copy method — the Dockerfile COPYs brand/ at build time)

# Secrets — do this once, never commit .env
cp .env.example .env
# Generate the secret key (set once, never change it — changing it
# invalidates every password on the site):
python3 -c "import secrets; print(secrets.token_hex(32))"
# Paste that value as APP_SECRET_KEY in .env, and set:
#   APP_BASE_URL=https://plugins.therustingdead.com
# Leave the PayPal keys empty for now: free downloads work, and paid
# checkout shows "payments are not configured yet" until sandbox keys
# are added (see PAYPAL-SETUP.md).

docker compose -f docker-compose.yml -f docker-compose.ovh.yml up -d --build
curl -s http://127.0.0.1:8000/health
docker compose -f docker-compose.yml -f docker-compose.ovh.yml logs -f rust-marketplace   # Ctrl-C to exit logs
```

Expected: `/health` returns ok, and `https://plugins.therustingdead.com`
serves the marketplace with your logo and horde banner once DNS has
propagated and Caddy has its certificate (a minute or two on first run).
Ports 80/443 on the box are Caddy's; nothing else needs to be exposed.
The marketplace itself only listens on 8000 inside the Compose network.

## Step 3 — First sign-in + smoke test

1. Register as `Realiztik` — the **first account is the admin**.
2. Home, Browse, a listing page, Forum, Feed, Services all load.
3. Sell → publish a test listing → Admin → approve it.
4. Free download works; paid checkout shows "payments are not
   configured yet" (expected until sandbox keys are in).
5. Check the logo/banner load and the hero (banner title under the
   headline) and the two-line wordmark.

## Step 4 — Iterate (the loop from here on)

Every change follows the same loop:

```bash
cd /data1/marketplace
git pull
docker compose -f docker-compose.yml -f docker-compose.ovh.yml up -d --build
curl -s http://127.0.0.1:8000/health
```

Back up `./data` before updates that touch the database:

```bash
cp -r data "data-backup-$(date +%Y-%m-%d)"
```

## After the site is live, in order

1. **PayPal sandbox test** (`PAYPAL-SETUP.md`): sandbox app + client
   ID/secret + webhook ID in `.env`, Platform Fee feature on, then a
   full sandbox checkout → capture → payout split → refund loop.
   Needs confirmation whether your already-linked PayPal is Business
   or Personal — that decides whether it can be the platform account.
2. **First listings:** Real Server Info ($19.99) when the `.cs` +
   description/changelog are ready, then WeightPlus, Kings and Lords,
   Z-Virus. TRD-Custom-Plugins repo + the ~180-plugin list via Eugene.
3. **Adopt the policies** (`POLICY-DRAFT.md`): review approve/flag/
   reject, refunds revoke download access, chargebacks absorbed by
   the platform — the RogueDepot model.
4. **Launch:** announce it; sellers connect PayPal by saving their
   merchant ID in the seller dashboard (manual for now — automated
   Partner Referrals onboarding needs PayPal partner approval).
