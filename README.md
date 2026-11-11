# Rust Marketplace — self-hosted plugin marketplace

A fully working marketplace website for Rust plugins, maps, tools, and
Discord bots, modelled on [RogueDepot](https://roguedepot.com/) (dark
theme, red accent, hero + stats + category tiles, listing pages with
tabs). Built for Realiztik to showcase his own plugins — including
**WeightPlus** and **AutoWipe_LGSM** — alongside other Rust work. It
will live at **plugins.therustingdead.com**.

Single container, no external services: Python 3.12 + FastAPI + SQLite
(file database) + server-rendered HTML. All state lives in `./data`.

## Payments — PayPal Commerce Platform (RogueDepot parity)

Payments match how RogueDepot handles them (verified from their Terms
and Creator Agreement, read 2026-11-09):

- **PayPal Commerce Platform only.** Buyer checkout and seller payouts
  both run through PayPal. **Stripe is set aside** — it was the v2
  payment method and is no longer wired into checkout.
- **15% platform fee, seller keeps 85%.** The split is recorded on
  every paid sale and in a payout ledger (seller dashboard + admin
  view). Free listings have no commission.
- **Instant payouts.** Sellers are paid the moment a sale completes,
  to the PayPal account they connected (their PayPal merchant ID, saved
  in the seller dashboard).
- **Refunds** — a seller or admin can refund a paid sale from the
  dashboard; the refund goes through PayPal and the buyer's download
  access is revoked.
- **Chargebacks are absorbed by the platform** — a seller never loses
  money from one. That is a business policy, not code: no chargeback
  handling is built.
- **No licence keys.** Buyers get download access from their library,
  plus a per-listing licence (use on any number of servers you own; no
  redistribution, resale, or sharing).

> **UNVERIFIED-LIVE:** the PayPal integration (`app/paypal_pay.py`)
> was written from PayPal's public developer docs and has never run
> against PayPal — no sandbox or live credentials have ever been
> provided. Do a full sandbox checkout end to end before treating it
> as working, and only switch `PAYPAL_MODE` to live deliberately after
> that. See "PayPal setup" below.

## Quick checklist — spin it up

1. **Copy the folder** to your host, e.g. `/opt/rust-marketplace`.
2. **Set the secret:** `cp .env.example .env`, then edit `.env` and set
   `APP_SECRET_KEY` to a long random string. Set it once and don't change
   it — it peppers password hashes, so changing it invalidates every
   password.
3. **Start it:** `docker compose up -d --build`
4. **Open it:** `http://<your-host>:8000` — check `/health` returns `{"status":"ok"}`.
5. **Create the first account** (Sign up). The first account on a fresh
   install becomes the **admin**. Tip: sign up as `Realiztik` — that
   claims the sample account that owns the WeightPlus and AutoWipe_LGSM
   listings, so they become yours.
6. **Point your Dynu domain at the host**, then add an Nginx Proxy Manager
   proxy host for the domain → `http://<host>:8000` (turn on Websockets
   Support for later live features). No other ports are exposed.
7. **Publish your first listing** (Sell) — it lands in the review queue.
   Approve it in **Admin → Review queue** and it goes live.
8. **Payments:** set the PayPal keys in `.env` (see "PayPal setup"),
   and connect a PayPal account from the **Seller dashboard** (merchant
   ID) before any paid listing can sell.

## What works in v3 (RogueDepot parity)

Everything in v1 and v2, plus:

- **PayPal Commerce checkout** — paid listings go through PayPal when
  keys are set (one order per checkout, one purchase unit per listing,
  each paying its seller instantly with the 15% platform fee). **With
  no keys configured, paid checkout shows a clear "payments are not
  configured yet" message and keeps paid items in the cart; free
  downloads still work.** No card details are ever stored. A PayPal
  webhook endpoint (`/paypal/webhook`) finalises purchases the
  success redirect misses, and only accepts signature-verified
  deliveries.
- **No licence keys** — removed. Purchases give library download
  access; the licence is per-listing text. Old purchase records keep
  their rows; no new keys are generated or shown.
- **Game is a first-class field** — every listing, category filter, and
  author page carries a game (Rust only for now; adding a game later is
  a config change in `app/config.py`, not a rebuild). Browse filters by
  game; author pages live at `/author/<username>`.
- **Review queue outcomes** — approve (goes live), flag for human
  review (typically 24–48 hours, seller emailed the reason), or reject
  with a specific reason (seller emailed the reason). Review covers
  security vulnerabilities, malicious code, code quality, performance
  issues, and listing completeness.
- **Refunds** — a seller can refund their own sales from the seller
  dashboard; an admin can refund any sale from the admin dashboard. A
  refund goes through PayPal (when the sale was a PayPal sale) and
  revokes the buyer's download access; refunded purchases can be
  bought again.
- **Commission accounting** — every paid sale records the 15% / 85%
  split and a row in the payout ledger. The seller dashboard shows
  earnings (85%), platform fees (15%), and recent sales with refund
  buttons. Admin sees platform fee totals across all sales.
- **Support tickets** — buyers open a ticket from a listing's Support
  tab or from their account. Sellers and admins reply in-thread;
  statuses are open / awaiting-seller / awaiting-buyer / resolved /
  closed. The nav shows a Tickets link with an open-ticket badge for
  sellers and admins. Ticket lists exist for buyer, seller, and admin.
- **Password reset** — forgot-password flow with a one-time token
  (hashed in the DB, 1-hour expiry, single use, sessions invalidated
  on reset). **Without SMTP configured, the reset link is shown on
  screen only to the requesting user in a clearly-labelled dev-mode
  notice** — it is never emailed anywhere and never written to a file.
  With SMTP configured, it is emailed instead.
- **Email notifications (optional SMTP)** — when SMTP is configured,
  mail is sent on: new sale (to seller), new ticket reply (to the
  other party), listing approved/flagged/rejected (to seller). With no
  SMTP, the site works fully without it and nothing is logged or shown.
- **Reporting + moderation** — logged-in users can report a listing or
  a user (reason + text). Reports land in an admin queue; an admin can
  dismiss a report or hide/remove the listing.
- **Seller dashboard** — `/seller`: your listings with status
  (pending/live/rejected/flagged/hidden), sales + earnings split,
  downloads, open tickets on your listings, and recent reviews. Linked
  from the account page.
- **Forum** — categories General, Plugin Help, Show Your Server;
  threads + replies, new-thread form for logged-in users, reply
  counts. Nav link "Forum" works.
- **Feed** — `/feed`: a real activity-feed page (new listings, updates,
  reviews, purchases) built from the existing events table. Nav link
  "Feed" works.
- **Nav matches RogueDepot** — Browse, Forum, Feed, Services, USD,
  Sign in / SIGN UP. **Services** is a real page (listing review,
  compile check, server-connect help). The **USD** selector is
  display-only and does not pretend to convert prices.

## PayPal setup

1. Create a PayPal developer account and open the sandbox dashboard:
   https://developer.paypal.com/dashboard/applications/sandbox
2. Create an app and copy its **client ID + secret** into `.env` as
   `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET`. Keep
   `PAYPAL_MODE=sandbox` until a full sandbox checkout works end to end.
3. On the app's settings page in the PayPal dashboard, enable the
   **Platform Fee** (PARTNER_FEE) feature — without it, order creation
   fails. The platform account also needs PayPal's approval for
   Commerce Platform marketplace use.
4. Set `APP_BASE_URL` to the real public URL of the site (used for
   PayPal return/cancel links and password-reset links).
5. Webhook (recommended): in the PayPal dashboard, add a webhook
   endpoint at `<APP_BASE_URL>/paypal/webhook` subscribed to
   `PAYMENT.CAPTURE.COMPLETED`, and set `PAYPAL_WEBHOOK_ID` from it.
   Without it, the webhook endpoint returns 400 and purchases are
   finalised by the success redirect only.
6. Sellers connect payouts from the **Seller dashboard**: save their
   PayPal merchant ID (PayPal → Account Settings → Business information
   → PayPal Merchant ID). A seller with no merchant ID saved cannot
   sell paid listings — checkout says so plainly.
7. To go live later: replace the sandbox keys with live keys
   deliberately in `.env` (never in git) and set `PAYPAL_MODE=live`
   plus the live webhook ID. Until then, no real money can move.

Still to do before real money (not code, setup): PayPal partner
approval for marketplace use, and the automated seller onboarding via
PayPal's Partner Referrals API (today sellers save a merchant ID
manually). Sandbox verification of the full checkout → capture →
payout → refund loop is also still outstanding — see the
UNVERIFIED-LIVE note above.

## Email / SMTP setup (optional)

Set in `.env`: `SMTP_HOST`, `SMTP_PORT` (default 587),
`SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`. With these set, the site sends
sale / ticket-reply / listing-decision emails and password-reset links
by email. With them unset, password reset shows the link on screen in
dev mode and no mail is sent. No credentials are ever logged.

## Seed data

On a fresh install (empty database) the site seeds itself:

- **WeightPlus** (Realiztik, WIP v2.0.6, unfinished) and
  **AutoWipe_LGSM** (Realiztik, v1.0.0) — Realiztik's real projects.
  Everything else is clearly fictional sample data, labelled as such
  in the listings themselves.

## Data & backup

- Database: `./data/marketplace.db` (SQLite). Uploads: `./data/uploads/`.
- **Back up `./data` and you have everything.** Copy the folder, or
  snapshot it before upgrades.
- Seeding is idempotent: it only runs when the database has no users.
  Sample users have no usable password — they exist so seeded reviews
  and listings have authors. Real users sign up normally.
- To reset to a clean seed: stop the container, delete
  `./data/marketplace.db` (and `./data/uploads/*` if you want), start
  again.

## Deliberately NOT in v3

- **Live PayPal payments** — the integration is written and wired in,
  but has never run against PayPal (no sandbox keys yet). Live keys are
  a deliberate `.env` change, not a code change — and only after a
  sandbox checkout works end to end.
- **Automated seller onboarding (Partner Referrals)** — sellers save a
  merchant ID manually for now; the referral-link flow needs PayPal
  partner approval first.
- **Live compile checking** — the badge is a recorded result, not a
  live compile.
- **Multi-currency** — USD only; the USD selector is display-only and
  does not convert prices.
- **Chargeback handling** — the platform absorbs chargebacks as a
  business policy; no code handles them.
- **Per-listing support SLAs / ticket assignment** — tickets are
  in-thread between buyer, seller, and admin only.
- **User banning / reporting a user beyond the queue** — user reports
  are recorded and shown to admins; there is no ban action yet.

## Development / local test

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
DATA_DIR=./data .venv/bin/python app.py   # serves on http://127.0.0.1:8000
```

## Security notes

- No secrets in this repo — only `.env.example` placeholders. Never
  commit a real `.env`.
- Uploads are limited to `.cs`, `.zip`, `.json`, `.md`, `.txt` (max
  20 MB), stored under a random prefix in `/data/uploads`, never
  executed. All user content is HTML-escaped; all SQL is parameterised.
- The app runs as a non-root user inside the container. Put it behind
  Nginx Proxy Manager (or another reverse proxy) with HTTPS — do not
  expose port 8000 directly to the internet.
