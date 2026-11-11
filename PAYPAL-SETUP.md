# PayPal setup for the Rusting Dead marketplace (plugins.therustingdead.com)

**Model (RogueDepot parity, verified from RogueDepot's Terms + Creator Agreement 2026-11-09):**
PayPal Commerce Platform only. Buyer checks out with PayPal; the seller is paid
instantly on every sale; the platform keeps a 15% commission (seller keeps 85%).
No Stripe. Prices in USD.

**Status (2026-11-10):** App code is built (PayPal module, 15% split, refunds,
review outcomes, game field). The PayPal flow is UNVERIFIED-LIVE — no sandbox
or live call has ever run. The steps below are what stands between here and
a proven sandbox purchase.

**Where keys live:** in the marketplace `.env` file on the host
(`PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_MODE`, `PAYPAL_WEBHOOK_ID`).
They never go in chat, files in the repo, or the Muse Secure Vault (the vault's
API flow only takes a single key; PayPal needs a client ID + secret pair).

## Step 0 — Confirm the existing PayPal is a Business account

Zach says a PayPal is already linked to the server. That account can be the
platform account **if it is a Business account**. Check: log in to PayPal →
Settings → Account Settings → Account type. It must say Business.
- Business → use it. For live scale, PayPal's Commerce Platform partner docs
  recommend a dedicated account that only receives platform fees — if the
  server account also takes donations or other payments, a separate Business
  account for the marketplace keeps the fee money clean. Not required for
  sandbox testing.
- Personal → it cannot run Commerce Platform marketplace payments. Upgrade it
  to Business (PayPal Settings → Upgrade to a Business account) or create a
  separate Business account for the marketplace.

## Step 1 — Sandbox REST app (for testing; do this first)

1. Log in to https://developer.paypal.com with the PayPal account.
2. Dashboard → **Apps & Credentials**. Make sure the toggle is on **Sandbox**.
3. **Create App**. Name it e.g. `TheRustingDead Marketplace`. Type: Merchant
   (or Platform if offered). Pick a sandbox business account to associate.
4. **Create App**. The app page shows the **Client ID** and the **Secret**.
   (Secret is shown once — copy it now.)
5. Add to the marketplace `.env` on the host:
   ```
   PAYPAL_MODE=sandbox
   PAYPAL_CLIENT_ID=<sandbox client id>
   PAYPAL_CLIENT_SECRET=<sandbox client secret>
   ```
6. Tell Muse the keys are in place (never paste the values in chat). Muse
   then runs the sandbox test purchase against the app.

## Step 2 — Sandbox test accounts

In the developer dashboard: **Testing Tools → Sandbox Accounts → Create account**.
Create two:
- A **Business** account (acts as a seller — used to test payouts).
- A **Personal** account (acts as a buyer — used to test checkout).
PayPal also auto-creates a facilitator business account; that one is the
default API-caller account. Give the buyer account a fake balance; no real
money moves in sandbox.

## Step 3 — Webhook (for capture/completion notifications)

1. In the sandbox app's settings (Apps & Credentials → the app), find
   **Webhooks** → Add webhook.
2. Subscribe to checkout-order and payment-capture events (at minimum:
   `CHECKOUT.ORDER.COMPLETED`, `PAYMENT.CAPTURE.COMPLETED`,
   `PAYMENT.CAPTURE.REFUNDED`).
3. Copy the **Webhook ID** into the `.env`:
   ```
   PAYPAL_WEBHOOK_ID=<webhook id>
   ```
The app verifies webhook signatures and only accepts `verification_status:
"SUCCESS"`. Without the webhook ID, the app cannot confirm captures.

## Step 4 — Platform Fee feature + partner approval (the uncertain step)

The 15% split uses PayPal's `platform_fees` on order capture. Two things
must be true:
- The **Platform Fee (PARTNER_FEE) feature** must be enabled for the app.
  Look for it in the app's feature settings in the developer dashboard.
- The platform account must be **approved by PayPal for Commerce Platform
  marketplace use**.
If the feature is not available in the dashboard, that is the partner-approval
step — it needs PayPal's help (contact PayPal support / your integration
contact). Do not assume it is on until a sandbox order with platform_fees
actually succeeds — that is the test in Step 6.

## Step 5 — Live (only when going live, after sandbox is proven)

Repeat Step 1 with the dashboard toggled to **Live**: create a live REST app,
copy the live client ID + secret, create a live webhook + ID, then in `.env`:
```
PAYPAL_MODE=live
PAYPAL_CLIENT_ID=<live client id>
PAYPAL_CLIENT_SECRET=<live client secret>
PAYPAL_WEBHOOK_ID=<live webhook id>
```
Never put live keys in while testing; never put sandbox keys in at launch.
Set a real `APP_SECRET_KEY` before going live (the app warns about the
dev-default fallback).

## Sellers — how they connect

Each seller connects their own PayPal account in the seller dashboard
(Account Settings → Business information → PayPal Merchant ID) by saving
their **PayPal Merchant ID** — found in their PayPal account under Settings →
Account Settings → Business information. Payouts go instantly to that account
on each sale. (Full automated onboarding via PayPal Partner Referrals is NOT
built yet — it needs partner approval first. Manual merchant-ID entry is the
launch path.)
Zach as a seller needs his own merchant ID saved the same way for Real
Server Info, WeightPlus, and his other listings.

## Verification checklist (sandbox, before launch)

- [ ] Sandbox purchase completes (buyer personal account → seller business
      account) and the buyer gets instant library access.
- [ ] The split lands: seller receives 85%, platform fee 15% recorded.
- [ ] A refund issued from the seller dashboard revokes the buyer's download
      access.
- [ ] A listing with no seller merchant ID blocks paid checkout with a plain
      message and leaves the item in the cart.
- [ ] Webhook deliveries arrive and verify (capture events confirmed).

## Sources

- PayPal "How do I create REST API credentials?" (paypal.com help) — Apps &
  Credentials → Create App → client ID + secret on the app page.
- PayPal Developer "Get started" — Commerce Platform (developer.paypal.com) —
  business accounts for API caller / partner fee / settlement; sandbox
  accounts under Testing Tools → Sandbox Accounts.
- PayPal Commerce Platform account-setup guide (GitHub, PayPal employee) —
  partner account should be a dedicated account for fee settlement.
