"""Rust plugin marketplace — SQLite storage layer.

Single SQLite file (DATA_DIR/marketplace.db) + uploads in DATA_DIR/uploads.
No separate database container. All queries are parameterised.
"""
import os
import sqlite3
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
DB_PATH = DATA_DIR / "marketplace.db"
UPLOAD_DIR = DATA_DIR / "uploads"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL DEFAULT '',
    salt TEXT NOT NULL DEFAULT '',
    is_admin INTEGER NOT NULL DEFAULT 0,
    is_sample INTEGER NOT NULL DEFAULT 0,
    bio TEXT NOT NULL DEFAULT '',
    -- PayPal merchant ID the seller connected for payouts (Account
    -- Settings > Business information > PayPal Merchant ID). Empty
    -- means the seller cannot receive paid sales yet.
    paypal_merchant_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    docs TEXT NOT NULL DEFAULT '',
    license_text TEXT NOT NULL DEFAULT '',
    support_text TEXT NOT NULL DEFAULT '',
    price_cents INTEGER NOT NULL DEFAULT 0,
    category TEXT NOT NULL,
    game TEXT NOT NULL DEFAULT 'rust',  -- first-class field; rust now
    version TEXT NOT NULL DEFAULT '1.0.0',
    compatibility TEXT NOT NULL DEFAULT 'Oxide',
    seller_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved |
    -- rejected | hidden | flagged (flagged = needs human review)
    review_note TEXT NOT NULL DEFAULT '',  -- reason given on flag/reject
    featured INTEGER NOT NULL DEFAULT 0,
    is_wip INTEGER NOT NULL DEFAULT 0,
    compile_status TEXT NOT NULL DEFAULT 'pending',  -- passed | failed | pending
    compile_date TEXT,
    views INTEGER NOT NULL DEFAULT 0,
    downloads INTEGER NOT NULL DEFAULT 0,
    purchases_count INTEGER NOT NULL DEFAULT 0,
    rating_avg REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    version TEXT NOT NULL,
    changelog TEXT NOT NULL DEFAULT '',
    filename TEXT,
    file_path TEXT,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    compile_status TEXT NOT NULL DEFAULT 'pending',
    compile_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    body TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (listing_id, user_id)
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, listing_id)
);

CREATE TABLE IF NOT EXISTS wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, listing_id)
);

CREATE TABLE IF NOT EXISTS reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    emoji TEXT NOT NULL DEFAULT '🔥',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (listing_id, user_id)
);

CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    amount_cents INTEGER NOT NULL DEFAULT 0,
    demo INTEGER NOT NULL DEFAULT 1,  -- 1 = demo checkout, no real money moved
    -- 15% / 85% split, recorded on every paid sale (0 for free/demo).
    platform_fee_cents INTEGER NOT NULL DEFAULT 0,
    seller_amount_cents INTEGER NOT NULL DEFAULT 0,
    paypal_order_id TEXT,
    paypal_capture_id TEXT,
    -- Refunds revoke download access (see has_purchase in main.py).
    refunded INTEGER NOT NULL DEFAULT 0,
    refunded_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Payout / earnings ledger: one row per paid sale. The seller is paid
-- instantly on capture by PayPal itself (INSTANT disbursement); this
-- table is the platform's record of the split, for the seller
-- dashboard and the admin view of platform fees.
CREATE TABLE IF NOT EXISTS payouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id INTEGER NOT NULL REFERENCES purchases(id),
    seller_id INTEGER NOT NULL REFERENCES users(id),
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    gross_cents INTEGER NOT NULL DEFAULT 0,
    platform_fee_cents INTEGER NOT NULL DEFAULT 0,
    seller_cents INTEGER NOT NULL DEFAULT 0,
    paypal_order_id TEXT,
    paypal_capture_id TEXT,
    status TEXT NOT NULL DEFAULT 'paid',  -- paid | refunded
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,  -- published | approved | purchase | review | download
    text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

-- v2 tables: support tickets, password resets, reports, forum.
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER REFERENCES listings(id),
    buyer_id INTEGER NOT NULL REFERENCES users(id),
    seller_id INTEGER REFERENCES users(id),
    subject TEXT NOT NULL,
    -- open | awaiting-seller | awaiting-buyer | resolved | closed
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ticket_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS password_resets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER NOT NULL REFERENCES users(id),
    listing_id INTEGER REFERENCES listings(id),
    reported_user_id INTEGER REFERENCES users(id),
    reason TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    -- open | dismissed | actioned
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS forum_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS forum_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES forum_categories(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS forum_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL REFERENCES forum_threads(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

"""


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns to existing installs (fresh installs get them via the
    schema only if the table already exists — ALTER is idempotent here
    because we check first)."""
    cols = {
        r["name"]
        for r in conn.execute("PRAGMA table_info(purchases)")
    }
    if "license_key" not in cols:
        conn.execute("ALTER TABLE purchases ADD COLUMN license_key TEXT")
    if "stripe_session_id" not in cols:
        conn.execute(
            "ALTER TABLE purchases ADD COLUMN stripe_session_id TEXT")
    if "stripe_payment_id" not in cols:
        conn.execute(
            "ALTER TABLE purchases ADD COLUMN stripe_payment_id TEXT")
    # v3 (RogueDepot parity): 15%/85% split, PayPal ids, refunds.
    if "platform_fee_cents" not in cols:
        conn.execute(
            "ALTER TABLE purchases ADD COLUMN platform_fee_cents "
            "INTEGER NOT NULL DEFAULT 0")
    if "seller_amount_cents" not in cols:
        conn.execute(
            "ALTER TABLE purchases ADD COLUMN seller_amount_cents "
            "INTEGER NOT NULL DEFAULT 0")
    if "paypal_order_id" not in cols:
        conn.execute("ALTER TABLE purchases ADD COLUMN paypal_order_id TEXT")
    if "paypal_capture_id" not in cols:
        conn.execute(
            "ALTER TABLE purchases ADD COLUMN paypal_capture_id TEXT")
    if "refunded" not in cols:
        conn.execute(
            "ALTER TABLE purchases ADD COLUMN refunded "
            "INTEGER NOT NULL DEFAULT 0")
    if "refunded_at" not in cols:
        conn.execute("ALTER TABLE purchases ADD COLUMN refunded_at TEXT")
    listing_cols = {
        r["name"] for r in conn.execute("PRAGMA table_info(listings)")
    }
    if "game" not in listing_cols:
        conn.execute(
            "ALTER TABLE listings ADD COLUMN game "
            "TEXT NOT NULL DEFAULT 'rust'")
    if "review_note" not in listing_cols:
        conn.execute(
            "ALTER TABLE listings ADD COLUMN review_note "
            "TEXT NOT NULL DEFAULT ''")
    user_cols = {
        r["name"] for r in conn.execute("PRAGMA table_info(users)")
    }
    if "paypal_merchant_id" not in user_cols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN paypal_merchant_id "
            "TEXT NOT NULL DEFAULT ''")


FORUM_CATEGORIES = [
    ("General", "Anything Rust — servers, wipes, news, chat."),
    ("Plugin Help", "Stuck with a plugin or a config? Ask here."),
    ("Show Your Server", "Show off your server, map or mod pack."),
]


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
        for name, desc in FORUM_CATEGORIES:
            conn.execute(
                "INSERT INTO forum_categories (name, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM forum_categories WHERE name = ?)",
                (name, desc, name),
            )
        conn.commit()
    finally:
        conn.close()


def is_empty() -> bool:
    conn = connect()
    try:
        row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
        return row["n"] == 0
    finally:
        conn.close()
