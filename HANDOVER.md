# Handover — The Rusting Dead Mod Marketplace (for Eugene)

Prepared 2026-11-10 23:14 PST by RealiztikkkBot (Muse), for Eugene to take
over the deploy and launch from here. Zach says you already have all the
accesses (SSH to the OVH box, Tailscale, etc.), so this is the state +
context you need, not an access request.

## What this is

A marketplace for Rust plugins, live target **https://plugins.therustingdead.com**,
for Zach (Realiztik), owner of The Rusting Dead server. Modelled on
RogueDepot (https://roguedepot.com/). **Rust-only to start**, other authors
can list and sell, paid + free, "game" is a first-class field from day one.

## The two links Zach is sending you

1. **Code + deploy guide:** https://github.com/realiztikkk/rust-marketplace
   (private, branch `main`) — the full build, deploy guide, PayPal setup,
   policy draft, README.
2. **Drive folder:** brand images + a copy of this handover — the two files
   that cannot go in the repo (see below).

## Current state (verified)

- **Payments: PayPal Commerce only, 15% platform fee** (creator keeps 85%).
  Matches RogueDepot exactly. Stripe was built, then set aside at launch
  (Stripe code deleted; only legacy DB migration columns mention it).
  Instant payouts per sale via PayPal `platform_fees` + payee merchant ID.
  Refunds revoke download access. **No license keys, no DRM.** Chargebacks
  are absorbed by the platform (business policy, see POLICY-DRAFT.md).
- **Review:** every listing reviewed — approve / flag / reject with reason.
  Compile check is a *recorded* result field, labelled as such — not a
  live compile.
- **Theme:** The Rusting Dead — Rust + Walking Dead comic style, logo +
  horde banner, dark with blood-red `#e11d2e`.
- **Name:** **The Rusting Dead Mod Marketplace** (decided 2026-11-10 14:43
  PST). "RustDepot" is out; "Plugin Arsenal" is taken by a live music-plugins
  site (pluginarsenal.com) — confusion risk, not a legal verdict.
- **First push:** commit `9ed5ce2cb93532142baeac9a1937af3ebd1f96de` (19 text
  files, verified by read-back). **Second push (this handover + OVH deploy
  files) is in flight / just landed — check the repo log for the commit
  after `9ed5ce2c` with message "Deploy target: OVH box".**
- **Preview v4** (static snapshot, not the build): link expires
  2026-11-12 15:32 PST — https://muse.ai/files/1485155001339978/1919070735945389/rsqhy5k8pjsomzyk525z69op/rustdepot-preview-v4.html
- **Deploy target DECIDED 2026-11-10 19:56 PST: the OVH game-server box**
  (51.222.245.218, user `rustserver`, Ubuntu 22.04.5) — NOT the home machine.
  The home machine runs ~80 containers incl. his sister's sites; the OVH
  box only runs the game server, so the blast radius is much narrower.

## Stack

Python 3.12 + FastAPI + SQLite, server-rendered HTML, no build step.
Single container, port 8000, volume `./data:/data` (SQLite DB + uploaded
plugin files — back up `./data` and you have everything). Caddy in front
for automatic HTTPS (`docker-compose.ovh.yml` + `Caddyfile`).

Repo layout: `app/` (main.py, db.py, auth.py, config.py, paypal_pay.py,
templates.py, mail.py, seed.py), `app.py`, `requirements.txt`,
`Dockerfile`, `docker-compose.yml`, `docker-compose.ovh.yml`, `Caddyfile`,
`.env.example`, `.gitignore`, `README.md`, `PAYPAL-SETUP.md`, `DEPLOY.md`,
`POLICY-DRAFT.md`, `brand/` (see below — **not in the repo**).

## What's NOT in the repo (in the Drive folder)

The GitHub connector cannot push binary files, so the two brand images
are **not** in the repo. Copy them into `brand/` on the box before
`docker compose up --build` — the Dockerfile `COPY brand/./brand/`
fails without them:

- `therustingdead-logo-512.png` (392,005 B, 512x512) — circular
  zombie-mouth logo, EST 2022
- `therustingdead-header.jpg` (181,238 B, 1024x512) — zombie horde banner,
  "THE RUSTING DEAD / HARDCORE - QUADS - ZOMBIES"

Also **not** in the repo (by design, not an oversight): `preview/` (static
HTML snapshots v1–v4 for Zach to view, not part of the build) and
`DEPLOY-OVH-DRAFT.md` — an early draft that **DEPLOY.md supersedes**;
delete it, it has a stale claim about SSH.

## Deploy — follow DEPLOY.md in the repo, summary here

1. **DNS (Dynu):** A record `plugins` → `51.222.245.218`. The wildcard
   currently points `plugins.therustingdead.com` at 198.18.137.13 — a
   specific record beats it. Do this BEFORE the first Caddy run, or Caddy
   cannot get its certificate.
2. **On the box:** `cd /data1 && git clone https://github.com/realiztikkk/rust-marketplace.git marketplace && cd marketplace`
   — then copy the two brand images into `brand/`.
3. **`.env`:** `cp .env.example .env`, generate `APP_SECRET_KEY`
   (`python3 -c "import secrets; print(secrets.token_hex(32))"`) — **set
   once, never change it** (changing it invalidates every password).
   Set `APP_BASE_URL=https://plugins.therustingdead.com`. Leave the PayPal
   keys **empty** for now: free downloads work, paid checkout shows
   "payments are not configured yet" until sandbox keys are added.
4. **Docker:** install status on the OVH box is **unknown** — check
   `docker --version`; install Docker Engine + Compose plugin if missing,
   add `rustserver` to the `docker` group.
5. **Up:** `docker compose -f docker-compose.yml -f docker-compose.ovh.yml up -d --build`,
   then `curl -s http://127.0.0.1:8000/health`. No web server was answering
   on the box (ports 80/443 checked 2026-11-10 19:29 PST, nothing) — Caddy
   will be the first one. Port 8000 stays internal; Caddy owns 80/443.
6. **Smoke test:** register as `Realiztik` (first account = admin), check
   Home / Browse / a listing / Forum / Feed / Services, publish a test
   listing → Admin → approve it, free download works, paid checkout shows
   "not configured yet". Check the logo/banner load, the hero (the banner
   has its own baked-in title under the hero headline — composition **not
   visually verified**), and the two-line nav wordmark (fit **not visually
   verified** on narrow widths).

## What is verified / what is not

Verified (fresh-DB boots, full flows, 2026-11-08–10): all pages 200;
logged-out 303s; free checkout; simulated paid sale + seller refund
(download revoked, payout row refunded); split math (1999→300/1699,
999→150/849, 499→75/424, 100→15/85, 1→0/1); review flag/reject with
reason; tickets; forum; password reset (dev-mode link on screen);
PayPal webhook rejects unsigned requests (400).

**NOT verified:** the PayPal live/sandbox flow — no credentials have ever
existed; needs sandbox keys + Platform Fee (PARTNER_FEE) feature enabled +
a webhook ID before the checkout → capture → payout → refund loop can be
proven (see PAYPAL-SETUP.md). Real SMTP sending not verified. The v1
transient `/login` bounce (one batch of requests bounced to /login, then
passed with no code change) never reappeared in v2 or the PayPal rebuild
— worth one re-check on the live host.

## PayPal setup (when ready — Zach deferred the sandbox test)

Guide: `PAYPAL-SETUP.md` in the repo. Zach says a PayPal is already linked
to the server — **Business vs Personal unconfirmed** (that decides whether
it can be the platform account). Steps: sandbox REST app (client ID +
secret → `.env`), sandbox test accounts, webhook
(CHECKOUT.ORDER.COMPLETED, PAYMENT.CAPTURE.COMPLETED,
PAYMENT.CAPTURE.REFUNDED → `PAYPAL_WEBHOOK_ID`), Platform Fee feature +
partner approval (the uncertain step — don't assume it's on until a
sandbox order with `platform_fees` succeeds), then live the same way.
Keys live in the marketplace `.env` on the host only — never in chat or
the repo. Sellers connect by saving their PayPal Merchant ID in the
seller dashboard (manual for now — Partner Referrals onboarding not built,
needs PayPal partner approval).

## Policies + first listings

- `POLICY-DRAFT.md` in the repo: review approve/flag/reject, refunds
  revoke download access, chargebacks absorbed by the platform — the
  RogueDepot model. **Still to be adopted as written** by Zach.
- First listing: **Real Server Info** ($19.99, planned for Codefling) —
  the `.cs` + description/changelog are not yet in hand. Then WeightPlus
  (his, **WIP — v2.0.6 unfinished, no successful compile, no release**),
  Kings and Lords, Z-Virus. Code lives in the **TRD-Custom-Plugins** repo
  on GitHub; the live server runs ~180 Oxide plugins — that list and repo
  access are your side of the fence, not mine.
- Seed data ships two of his listings (WeightPlus + AutoWipe_LGSM) owned
  by a sample "Realiztik" account — he claims it by signing up with
  username `Realiztik` (first account = admin). The other 8 seeded
  listings are clearly fictional, labelled SAMPLE.

## Access notes (for context, not requests)

- My SSH key was **never added** to the OVH box (or the home machine) —
  nothing of mine to revoke. The home-machine Tailscale approval is no
  longer needed for this deploy.
- Outbound SSH from my VM is off; I reached services only through the
  Tailscale tunnel proxy. That constraint is mine, not yours.
- The marketplace `.env` must never be committed (`.gitignore` covers it)
  and must never contain a real secret in the repo.
- Zach's rules that still apply: approval-first for live changes, and all
  changes recorded in the git repo (pushes go through the repo; the
  iterate loop is `git pull` + `docker compose up -d --build` on the box).

## Order of work from here

1. Deploy on the OVH box + smoke test (above).
2. PayPal sandbox test on the live site (when Zach is ready).
3. First listings (Real Server Info, then the rest).
4. Adopt POLICY-DRAFT.md.
5. Launch.
