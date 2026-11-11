# Deploy — The Rusting Dead Mod Marketplace

How to get the marketplace live on `plugins.therustingdead.com` so we can
test and improve it iteratively. One container, one volume, behind the
Nginx Proxy Manager you already run.

## What is already ready

- `Dockerfile` — Python 3.12-slim, non-root, healthcheck on `/health`,
  ships `app/` + `brand/` (logo + banner).
- `docker-compose.yml` — one service, port `8000`, volume `./data:/data`
  (SQLite DB + uploaded plugin files). All state lives in `./data`;
  back that folder up and you have everything.
- `.env.example` — every setting, with PayPal sandbox first.
- `PAYPAL-SETUP.md` — the PayPal sandbox walkthrough (separate step,
  after the site is up).
- `POLICY-DRAFT.md` — review / refund / chargeback policies drafted
  from RogueDepot (still to be adopted as written).

## Step 0 — Get the code onto the host (the one gap)

The code currently lives only in Muse's workspace, not in a GitHub repo
yet. Pick one:

**A. GitHub repo (recommended for iterating).** I create a repo
(e.g. `realiztikkk/rust-marketplace`), push the code, and every update
is `git pull` + rebuild on the host. Needs your approval to create the
repo and push.

**B. Copy the folder yourself.** Zip / `rsync` this folder to the host
over SSH/Tailscale and skip GitHub for now. Works, but every update is
another manual copy.

**C. I deploy it directly.** Set up my own Tailscale access to your
home machine (separate from Eugene's access) and I run the deploy
commands on the host for you.

## Step 1 — On the host

```bash
# Suggested home, next to your other sites in /opt/mysites
cd /opt/mysites
git clone https://github.com/realiztikkk/rust-marketplace.git marketplace
cd marketplace

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

docker compose up -d --build
curl -s http://127.0.0.1:8000/health
docker compose logs -f rust-marketplace   # Ctrl-C to exit logs
```

Expected: `/health` returns ok, home page loads at
`http://<host>:8000`. Port 8000 is only for the LAN — do **not**
forward it on the router; the public entry is NPM (Step 3).

## Step 2 — DNS (Dynu)

Add an `A` record in Dynu:

- Host: `plugins`
- Domain: `therustingdead.com`
- Value: your public IP (same one your other sites use)

If your public IP changes, Dynu's dynamic-DNS updater keeps it
pointed at the host.

## Step 3 — Nginx Proxy Manager

Add a proxy host:

- Domain: `plugins.therustingdead.com`
- Scheme: `http`, Forward Hostname/IP: `192.168.1.103`, Forward Port: `8000`
- SSL: request a Let's Encrypt certificate, Force SSL on
- Websockets Support: on (harmless now, needed if live features land later)

Then open `https://plugins.therustingdead.com` — you should see the
marketplace with your logo and horde banner.

## Step 4 — First sign-in + smoke test

1. Register as `Realiztik` — the **first account is the admin**.
2. Home, Browse, a listing page, Forum, Feed, Services all load.
3. Sell → publish a test listing → Admin → approve it.
4. Free download works; paid checkout shows "payments are not
   configured yet" (expected until sandbox keys are in).
5. Check the logo/banner load and the hero (banner title under the
   headline) and the two-line wordmark.

## Step 5 — Iterate (the loop from here on)

Every change follows the same loop:

```bash
cd /opt/mysites/marketplace
git pull            # or re-copy the folder, if you went with option B
docker compose up -d --build
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
