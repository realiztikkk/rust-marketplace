# Seller & buyer policies — DRAFT, not live

- Status: **draft only, staged 2026-11-10 (evening PST) by Muse**. Nothing here is
  wired into the app and no page exists for it yet — there is no `/terms`,
  `/policies`, or refund-policy route in `app/main.py` today. Wiring it in
  (as pages and footer links) needs Realiztik's approval, like any other
  change to the live build.
- Source of every clause: decisions Realiztik already made (PayPal Commerce
  only, 15% fee) plus the RogueDepot
  handling verified from RogueDepot's Terms + Creator Agreement on
  2026-11-09, as recorded in `README.md` and
  `00-inbox-staging/marketplace-agent-brief-therustingdead-2026-11-09-ANSWER.md`.
- Open call: Realiztik has not yet said yes to adopting RogueDepot's review,
  refund, and chargeback policies as written (that was step 4 of the launch
  path). This draft assumes yes; if he wants different wording, this file is
  the place to change it before it goes on the site.
- Honest limits, carried over from the README: the PayPal checkout → capture
  → payout loop has never run against PayPal (no sandbox keys yet), the
  Platform Fee feature + PayPal partner approval are outstanding, and the
  compile-check badge is a recorded result, not a live compile — so this
  draft says "compile check shown" and does not promise live compiling.

---

# The Rusting Dead Mod Marketplace — Seller & Buyer Policies

**The Rusting Dead Mod Marketplace** (plugins.therustingdead.com) is a
marketplace for Rust plugins. Rust-only at launch. Other authors can list
and sell alongside Realiztik's own plugins.

## Payments

- Payments run on **PayPal Commerce Platform only** — buyer checkout and
  seller payouts both go through PayPal. No other payment method is offered
  at launch.
- Prices are in **USD** only.
- **Platform fee: 15% of every paid sale. The seller keeps 85%.** The split
  is recorded on every sale and shown in the seller dashboard and the admin
  view. Free listings have no commission.
- **Payouts are instant.** When a sale completes, the seller is paid at once
  to the PayPal account they connected. There is no holding period and no
  minimum payout stated.
- To sell paid listings, a seller must connect a PayPal account by saving
  their **PayPal Merchant ID** in the seller dashboard (Account Settings →
  Business information). A seller with no merchant ID saved cannot sell paid
  listings. Automated onboarding (PayPal Partner Referrals) is not built yet.
- No card details are ever stored by the marketplace.

## Downloads, licences, and library access

- There are **no licence keys**. Buying a plugin gives download access from
  the buyer's account library.
- The per-listing licence allows use on any number of servers the buyer owns
  and operates. The buyer may not redistribute, resell, or share the plugin
  files, and may not claim ownership of the plugin. A seller may write their
  own licence text for a listing instead.
- Uploaded files are plugin files (`.cs`, `.zip`, `.json`, `.md`, `.txt`,
  max 20 MB). Uploads are stored, never executed by the marketplace.

## Listing review — every listing is reviewed before it goes live

- Every listing is reviewed before it goes live. Outcomes:
  - **Approved** — the listing goes live.
  - **Flagged for human review** — typically within 24–48 hours; the seller
    is emailed the reason.
  - **Rejected, with reasons** — the seller is emailed the reason.
- Review covers: security vulnerabilities, malicious code, code quality,
  performance issues, and listing completeness. A compile check is shown on
  the listing.
- A listing goes into the review queue when submitted and is not live until
  an admin approves it.

## Refunds

- Refunds are **at the seller's discretion**.
- A seller can refund their own sales from the seller dashboard; an admin
  can refund any sale from the admin dashboard.
- A refund goes through PayPal (when the sale was a PayPal sale) and
  **revokes the buyer's download access**. A refunded purchase can be bought
  again.
- Refund requests go through the listing's Support tab or the buyer's
  account (support tickets), so seller and admin can reply in-thread.

## Chargebacks

- **The platform absorbs chargeback costs.** A seller never loses money
  from a chargeback on one of their sales. (Business policy — no chargeback
  handling is built into the app.)

## Support, reporting, and moderation

- Buyers open a support ticket from a listing's Support tab or from their
  account; sellers and admins reply in-thread. Statuses: open,
  awaiting-seller, awaiting-buyer, resolved, closed.
- Logged-in users can report a listing or a user. Reports land in an admin
  queue; an admin can dismiss a report or hide/remove the listing.
- Listings, reviews, and forum posts are moderated; the marketplace may
  remove content that breaks these policies.

## What is still to do before real money moves

- PayPal sandbox test of the full checkout → capture → payout → refund loop
  (needs sandbox keys + Platform Fee feature enabled + webhook ID).
- PayPal partner approval for Commerce Platform marketplace use.
- This policy text approved by Realiztik, then published as site pages.
