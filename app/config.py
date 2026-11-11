"""Shared marketplace configuration — environment-based, no secrets here.

BASE_URL is the public URL of the site (used for PayPal return/cancel
links and password-reset links). COMMISSION_RATE is the platform fee
taken on every paid sale (15% — RogueDepot parity; the seller keeps
85%). GAMES is the list of games the marketplace covers: Rust only for
now — adding a game later is a config change here, not a rebuild.
DEFAULT_LICENSE_TEXT is the per-listing licence buyers get when a
seller does not write their own.
"""
import os

BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")

COMMISSION_RATE = 0.15
COMMISSION_PCT = 15

# (slug, display name). Rust-only for now.
GAMES = [("rust", "Rust")]

DEFAULT_LICENSE_TEXT = (
    "This license allows you to use this plugin on any number of servers "
    "you own and operate. You may not redistribute, resell, or share the "
    "plugin files. You may not claim ownership of the plugin."
)


def split_cents(amount_cents: int) -> tuple[int, int]:
    """Split a paid sale into (platform_fee_cents, seller_cents).

    Free listings (0) have no commission. The fee is 15% of the sale,
    rounded to the nearest cent; the seller gets the rest.
    """
    if amount_cents <= 0:
        return 0, 0
    fee = int(round(amount_cents * COMMISSION_RATE))
    return fee, amount_cents - fee
