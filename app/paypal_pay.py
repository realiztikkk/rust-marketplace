"""PayPal Commerce Platform — marketplace checkout + instant payouts.

UNVERIFIED-LIVE — read this before trusting it with real money:
This module was written from PayPal's public developer documentation
(Orders API v2; Commerce Platform "Capture and instant transfer" and
"Accept multi-merchant payments", read 2026-11-09). No sandbox or live
credentials have ever been provided, so no call in this module has ever
run against PayPal. The first sandbox checkout must be tested end to
end before this is treated as working.

How it is meant to work (RogueDepot parity):
- Buyer checks out with PayPal. One PayPal order holds one purchase
  unit per paid listing (max 10 units per order, per PayPal's
  multi-merchant docs); each unit names its seller as payee.
- Each unit carries payment_instruction {disbursement_mode: "INSTANT",
  platform_fees: [{amount: 15% of the price}]}. On capture, PayPal
  sends the seller 85% instantly and the platform keeps the 15% fee.
- Sellers connect a PayPal account by saving their PayPal merchant ID
  in the seller dashboard (Account Settings > Business information >
  PayPal Merchant ID). The full production onboarding is PayPal's
  Partner Referrals API, which generates a signup link and returns the
  seller's merchant ID — that flow is NOT implemented here yet; it needs
  PayPal partner approval first. See README "PayPal setup".
- platform_fees also needs the "Platform Fee" (PARTNER_FEE) feature
  enabled for the app in the PayPal developer dashboard, and the
  platform account must be approved by PayPal for Commerce Platform
  marketplace use. Without that, order creation fails with a PayPal
  error — which this module surfaces plainly instead of guessing.

Config only from the environment:
  PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET — the platform's app keys.
  PAYPAL_MODE — "sandbox" (default) or "live". Live is never used
    unless the operator deliberately sets it in .env.
  PAYPAL_WEBHOOK_ID — the webhook ID from the developer dashboard;
    required for webhook signature verification.
  PAYPAL_BN_CODE — optional partner attribution ID.
With no keys configured, paypal_enabled() is False and paid checkout
must show "payments are not configured yet" — free downloads still
work. No real money is ever charged by this code on its own.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request

PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox").lower()
PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID", "")
PAYPAL_BN_CODE = os.environ.get("PAYPAL_BN_CODE", "")

_SANDBOX_BASE = "https://api-m.sandbox.paypal.com"
_LIVE_BASE = "https://api-m.paypal.com"

# In-memory OAuth token cache: {"token": str, "expires_at": float}.
_TOKEN: dict = {}


class PayPalError(Exception):
    """A PayPal API call failed (network or an error body from PayPal)."""


def paypal_enabled() -> bool:
    return bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)


def is_live() -> bool:
    return PAYPAL_MODE == "live"


def api_base() -> str:
    return _LIVE_BASE if is_live() else _SANDBOX_BASE


def money(cents: int) -> str:
    """Cents -> PayPal amount string with two decimals, e.g. 1999 -> "19.99"."""
    return f"{cents / 100:.2f}"


def _request(method: str, path: str, body: dict | None = None,
             extra_headers: dict | None = None) -> dict:
    """One authenticated PayPal API call. Returns the parsed JSON body.

    Raises PayPalError with PayPal's own error message (name + message
    from the error body) on any non-2xx response or network failure.
    Never logs or raises with credentials in the message.
    """
    token = _access_token()
    url = api_base() + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if PAYPAL_BN_CODE:
        headers["PayPal-Partner-Attribution-Id"] = PAYPAL_BN_CODE
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8") or "{}")
        except Exception:
            err = {}
        detail = err.get("message") or err.get("name") or f"HTTP {e.code}"
        raise PayPalError(f"PayPal {method} {path} failed: {detail}")
    except urllib.error.URLError as e:
        raise PayPalError(f"PayPal {method} {path} unreachable: {e.reason}")


def _access_token() -> str:
    """OAuth2 client-credentials token, cached until shortly before expiry."""
    now = time.time()
    if _TOKEN.get("token") and _TOKEN.get("expires_at", 0) > now + 60:
        return _TOKEN["token"]
    credentials = base64.b64encode(
        f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()
    ).decode()
    req = urllib.request.Request(
        api_base() + "/v1/oauth2/token",
        data=b"grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise PayPalError(
            f"PayPal token request failed: HTTP {e.code} — check "
            "PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET and PAYPAL_MODE."
        )
    except urllib.error.URLError as e:
        raise PayPalError(f"PayPal token request unreachable: {e.reason}")
    _TOKEN["token"] = payload["access_token"]
    _TOKEN["expires_at"] = now + int(payload.get("expires_in", 300))
    return _TOKEN["token"]


def auth_assertion(merchant_id: str) -> str:
    """PayPal-Auth-Assertion JWT for calls made on behalf of one seller.

    Per PayPal's "Capture and instant transfer" docs: header {"alg":
    "none"}, payload {"iss": <platform client_id>, "payer_id": <seller
    payer/merchant id>}. Used when a checkout has a single seller; for
    multi-seller carts the order relies on the per-unit payee fields
    instead (see create_order).
    """
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    payload = base64.urlsafe_b64encode(
        json.dumps(
            {"iss": PAYPAL_CLIENT_ID, "payer_id": merchant_id}
        ).encode()
    ).decode().rstrip("=")
    return f"{header}.{payload}."


def create_order(user_id: int, units: list, return_url: str,
                 cancel_url: str) -> dict:
    """Create a PayPal order for the given paid cart items.

    units: list of dicts with keys listing_id, title, amount_cents,
    fee_cents, seller_merchant_id. One purchase unit per item (max 10,
    per PayPal's multi-merchant docs). Each unit pays its seller
    (payee.merchant_id) with INSTANT disbursement and the 15% platform
    fee. Returns the order object, which includes links — the caller
    redirects the buyer to the link with rel == "approve".
    Raises PayPalError if PayPal is not configured or rejects the order
    (e.g. Platform Fee feature not enabled, seller not onboarded).
    """
    if not paypal_enabled():
        raise PayPalError("PayPal is not configured (no client keys).")
    if not units:
        raise PayPalError("No paid items to check out.")
    if len(units) > 10:
        raise PayPalError(
            "PayPal allows at most 10 purchase units per order — split "
            "the cart and check out in two goes.")
    purchase_units = []
    for u in units:
        if not u.get("seller_merchant_id"):
            raise PayPalError(
                f"The seller of '{u['title']}' has not connected a PayPal "
                "account for payouts yet, so this listing cannot be sold "
                "through PayPal right now."
            )
        purchase_units.append({
            "reference_id": f"listing-{u['listing_id']}",
            "custom_id": f"user-{user_id}",
            "description": u["title"][:127],
            "amount": {
                "currency_code": "USD",
                "value": money(u["amount_cents"]),
            },
            "payee": {"merchant_id": u["seller_merchant_id"]},
            "payment_instruction": {
                "disbursement_mode": "INSTANT",
                "platform_fees": [{
                    "amount": {
                        "currency_code": "USD",
                        "value": money(u["fee_cents"]),
                    },
                }],
            },
        })
    body = {
        "intent": "CAPTURE",
        "purchase_units": purchase_units,
        "application_context": {
            "brand_name": "The Rusting Dead Mod Marketplace",
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "PAY_NOW",
        },
    }
    extra = None
    seller_ids = {u["seller_merchant_id"] for u in units}
    if len(seller_ids) == 1:
        # Single-seller checkout: act on that seller's behalf, per
        # PayPal's instant-transfer docs.
        extra = {"PayPal-Auth-Assertion": auth_assertion(seller_ids.pop())}
    return _request("POST", "/v2/checkout/orders", body, extra)


def approval_url(order: dict) -> str | None:
    """The buyer-approval URL from a created order, or None."""
    for link in order.get("links", []):
        if link.get("rel") == "approve":
            return link.get("href")
    return None


def capture_order(order_id: str) -> dict:
    """Capture an approved order. Returns the captured order object."""
    return _request("POST", f"/v2/checkout/orders/{order_id}/capture", {})


def get_order(order_id: str) -> dict:
    """Fetch an order's current state (used by the webhook handler)."""
    return _request("GET", f"/v2/checkout/orders/{order_id}")


def refund_capture(capture_id: str, amount_cents: int) -> dict:
    """Refund a captured payment (full amount of the capture is the
    normal case). Returns the refund object."""
    return _request(
        "POST", f"/v2/payments/captures/{capture_id}/refund",
        {"amount": {"currency_code": "USD", "value": money(amount_cents)}},
    )


def parse_captured_units(order: dict) -> list:
    """Extract per-listing capture info from a captured order.

    Returns a list of dicts: {listing_id, user_id, capture_id, amount_cents}.
    Units without a capture (e.g. declined) are skipped. The listing id
    comes from the purchase unit's reference_id ("listing-<id>") and the
    buyer from its custom_id ("user-<id>").
    """
    out = []
    for unit in order.get("purchase_units", []):
        ref = (unit.get("reference_id") or "")
        custom = (unit.get("custom_id") or "")
        if not ref.startswith("listing-") or not custom.startswith("user-"):
            continue
        captures = (unit.get("payments") or {}).get("captures") or []
        for cap in captures:
            if cap.get("status") != "COMPLETED":
                continue
            amount = cap.get("amount") or {}
            try:
                cents = int(round(float(amount.get("value", "0")) * 100))
            except (TypeError, ValueError):
                cents = 0
            out.append({
                "listing_id": int(ref.split("-", 1)[1]),
                "user_id": int(custom.split("-", 1)[1]),
                "capture_id": cap.get("id"),
                "amount_cents": cents,
            })
    return out


def verify_webhook(headers, raw_body: bytes) -> bool:
    """Verify a PayPal webhook delivery against PayPal's API.

    headers is a mapping with the five paypal-* headers PayPal sends.
    The raw body is embedded verbatim — re-serialising the JSON can
    change bytes and break verification, per PayPal's docs. Returns
    True only when PayPal answers verification_status == "SUCCESS".
    Requires PAYPAL_WEBHOOK_ID. Raises PayPalError on API failure.
    """
    if not PAYPAL_WEBHOOK_ID:
        raise PayPalError("PAYPAL_WEBHOOK_ID is not configured.")
    # Build the verify body as text so the event goes through byte-for-byte.
    verify_body = (
        '{"auth_algo":' + json.dumps(headers.get("paypal-auth-algo", ""))
        + ',"cert_url":' + json.dumps(headers.get("paypal-cert-url", ""))
        + ',"transmission_id":'
        + json.dumps(headers.get("paypal-transmission-id", ""))
        + ',"transmission_sig":'
        + json.dumps(headers.get("paypal-transmission-sig", ""))
        + ',"transmission_time":'
        + json.dumps(headers.get("paypal-transmission-time", ""))
        + ',"webhook_id":' + json.dumps(PAYPAL_WEBHOOK_ID)
        + ',"webhook_event":' + raw_body.decode("utf-8") + '}'
    )
    token = _access_token()
    req = urllib.request.Request(
        api_base() + "/v1/notifications/verify-webhook-signature",
        data=verify_body.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        raise PayPalError(f"PayPal webhook verification failed: HTTP {e.code}")
    except urllib.error.URLError as e:
        raise PayPalError(f"PayPal webhook verification unreachable: {e.reason}")
    return result.get("verification_status") == "SUCCESS"
