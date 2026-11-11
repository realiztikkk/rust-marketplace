"""The Rusting Dead Mod Marketplace — FastAPI app.

Single container, SQLite file DB, server-rendered HTML. Payments run
on the PayPal Commerce Platform (buyer checkout + instant seller
payouts, 15% platform fee / 85% seller), matching RogueDepot. Stripe
was the v2 payment method and is set aside — it is no longer wired
into checkout. The PayPal flow is UNVERIFIED-LIVE (see
app/paypal_pay.py): no sandbox or live credentials have ever been
provided, so no PayPal call has run yet.
"""
import hashlib
import json
import os
import re
import secrets
import sqlite3
import string
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import auth, mail, paypal_pay, templates
from .config import (BASE_URL, COMMISSION_PCT, DEFAULT_LICENSE_TEXT,
                     GAMES, split_cents)
from .db import DATA_DIR, UPLOAD_DIR, connect, init_db, is_empty
from .seed import seed as seed_data

APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY", "dev-only-change-me")
ALLOWED_EXTS = {".cs", ".zip", ".json", ".md", ".txt"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
PAGE_SIZE = 12


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if is_empty():
        seed_data()
    yield


app = FastAPI(title="The Rusting Dead Mod Marketplace", lifespan=lifespan)

# Brand assets (The Rusting Dead logo + header banner) served from brand/.
BRAND_DIR = Path(__file__).resolve().parent.parent / "brand"
app.mount("/brand", StaticFiles(directory=BRAND_DIR), name="brand")


# ---- helpers ---------------------------------------------------------------

def get_user(request: Request):
    return auth.get_user_from_token(request.cookies.get("session_token"))


def flash_redirect(url: str, kind: str, msg: str) -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    return RedirectResponse(
        f"{url}{sep}flash_kind={kind}&flash_msg={msg}", status_code=303
    )


def read_flash(request: Request):
    kind = request.query_params.get("flash_kind", "")
    msg = request.query_params.get("flash_msg", "")
    return (kind, msg) if msg else ""


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "listing"
    return slug


def unique_slug(conn, title: str) -> str:
    base = slugify(title)
    slug = base
    n = 2
    while conn.execute(
        "SELECT 1 FROM listings WHERE slug = ?", (slug,)
    ).fetchone():
        slug = f"{base}-{n}"
        n += 1
    return slug


def save_upload(upload: UploadFile | None) -> tuple[str | None, str | None, int]:
    """Validate and store an uploaded file. Returns (filename, path, size)."""
    if upload is None or not upload.filename:
        return None, None, 0
    ext = Path(upload.filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise ValueError(
            f"File type {ext} not allowed. Use: {', '.join(sorted(ALLOWED_EXTS))}"
        )
    data = upload.file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("File is over the 20 MB limit.")
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(upload.filename).name)
    stored = f"{secrets.token_hex(8)}_{safe_name}"
    path = UPLOAD_DIR / stored
    path.write_bytes(data)
    return safe_name, str(path), len(data)


def record_event(conn, kind: str, text: str) -> None:
    conn.execute("INSERT INTO events (kind, text) VALUES (?, ?)", (kind, text))


def recompute_rating(conn, listing_id: int) -> None:
    row = conn.execute(
        "SELECT AVG(rating) AS avg FROM reviews WHERE listing_id = ?",
        (listing_id,),
    ).fetchone()
    conn.execute(
        "UPDATE listings SET rating_avg = ? WHERE id = ?",
        (row["avg"] or 0, listing_id),
    )


def get_settings(conn) -> dict:
    return {
        r["key"]: r["value"]
        for r in conn.execute("SELECT key, value FROM settings")
    }


def has_purchase(conn, user_id: int, listing_id: int) -> bool:
    """True if the user owns the listing. A refunded purchase does NOT
    count — a refund revokes download access, and the buyer may buy
    again."""
    return bool(
        conn.execute(
            "SELECT 1 FROM purchases WHERE user_id = ? AND listing_id = ?"
            " AND refunded = 0",
            (user_id, listing_id),
        ).fetchone()
    )


# ---- public pages ----------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = get_user(request)
    conn = connect()
    try:
        stats = conn.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN price_cents = 0 THEN 1 ELSE 0 END) AS free,
                      COALESCE(SUM(downloads), 0) AS downloads
               FROM listings WHERE status = 'approved'"""
        ).fetchone()
        users = conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE is_sample = 0"
        ).fetchone()
        featured = conn.execute(
            "SELECT * FROM listings WHERE status='approved' AND featured=1 "
            "ORDER BY downloads DESC LIMIT 4"
        ).fetchall()
        newest = conn.execute(
            "SELECT * FROM listings WHERE status='approved' "
            "ORDER BY created_at DESC, id DESC LIMIT 4"
        ).fetchall()
        events = conn.execute(
            "SELECT text FROM events ORDER BY id DESC LIMIT 8"
        ).fetchall()
        settings = get_settings(conn)
        return templates.home_page(
            user,
            {"total": stats["total"], "free": stats["free"] or 0,
             "downloads": stats["downloads"], "users": users["n"]},
            [dict(r) for r in featured],
            [dict(r) for r in newest],
            [dict(r) for r in events],
            settings,
            flash=read_flash(request),
        )
    finally:
        conn.close()


@app.get("/browse", response_class=HTMLResponse)
def browse(request: Request, q: str = "", category: str = "", sort: str = "newest",
           price: str = "all", page: int = 1, game: str = ""):
    user = get_user(request)
    conn = connect()
    try:
        where = ["status = 'approved'"]
        params: list = []
        if q:
            where.append("(title LIKE ? OR description LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        if category in templates.CATEGORIES:
            where.append("category = ?")
            params.append(category)
        if game in [g[0] for g in GAMES]:
            where.append("game = ?")
            params.append(game)
        if price == "free":
            where.append("price_cents = 0")
        elif price == "paid":
            where.append("price_cents > 0")
        order = {
            "newest": "created_at DESC, id DESC",
            "downloads": "downloads DESC",
            "rating": "rating_avg DESC",
            "price_asc": "price_cents ASC",
            "price_desc": "price_cents DESC",
        }.get(sort, "created_at DESC, id DESC")
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM listings WHERE {' AND '.join(where)}",
            params,
        ).fetchone()["n"]
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(1, min(page, pages))
        rows = conn.execute(
            f"SELECT * FROM listings WHERE {' AND '.join(where)} "
            f"ORDER BY {order} LIMIT ? OFFSET ?",
            params + [PAGE_SIZE, (page - 1) * PAGE_SIZE],
        ).fetchall()
        return templates.browse_page(
            user, [dict(r) for r in rows], q, category, sort, price, page,
            pages, total, game=game,
            flash=read_flash(request),
        )
    finally:
        conn.close()


@app.get("/listing/{slug}", response_class=HTMLResponse)
def listing_detail(request: Request, slug: str, tab: str = "details"):
    user = get_user(request)
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE slug = ? AND status = 'approved'",
            (slug,),
        ).fetchone()
        if not row:
            return HTMLResponse(
                templates.layout("Not found", user,
                                 "<div class='wrap'><div class='section'>"
                                 "<h2>Listing not found</h2>"
                                 "<p class='muted'>It may still be in the "
                                 "review queue, or the link is wrong.</p>"
                                 "</div></div>"),
                status_code=404,
            )
        listing = dict(row)
        conn.execute(
            "UPDATE listings SET views = views + 1 WHERE id = ?",
            (listing["id"],),
        )
        conn.commit()
        listing["views"] += 1
        seller = dict(conn.execute(
            "SELECT * FROM users WHERE id = ?", (listing["seller_id"],)
        ).fetchone())
        versions = [dict(r) for r in conn.execute(
            "SELECT * FROM versions WHERE listing_id = ? ORDER BY id DESC",
            (listing["id"],),
        )]
        reviews = [dict(r) for r in conn.execute(
            """SELECT r.*, u.username FROM reviews r
               JOIN users u ON u.id = r.user_id
               WHERE r.listing_id = ? ORDER BY r.id DESC""",
            (listing["id"],),
        )]
        comments = [dict(r) for r in conn.execute(
            """SELECT c.*, u.username FROM comments c
               JOIN users u ON u.id = c.user_id
               WHERE c.listing_id = ? ORDER BY c.id ASC""",
            (listing["id"],),
        )]
        in_cart = in_wishlist = reacted = False
        owned = False
        if user:
            in_cart = bool(conn.execute(
                "SELECT 1 FROM cart_items WHERE user_id=? AND listing_id=?",
                (user["id"], listing["id"])).fetchone())
            in_wishlist = bool(conn.execute(
                "SELECT 1 FROM wishlist WHERE user_id=? AND listing_id=?",
                (user["id"], listing["id"])).fetchone())
            reacted = bool(conn.execute(
                "SELECT 1 FROM reactions WHERE user_id=? AND listing_id=?",
                (user["id"], listing["id"])).fetchone())
            owned = (
                user["id"] == listing["seller_id"]
                or has_purchase(conn, user["id"], listing["id"])
            )
        reaction_count = conn.execute(
            "SELECT COUNT(*) AS n FROM reactions WHERE listing_id = ?",
            (listing["id"],),
        ).fetchone()["n"]
        if tab not in ("details", "docs", "reviews", "discussion",
                       "versions", "support", "license"):
            tab = "details"
        return templates.listing_page(
            user, listing, seller, versions, reviews, comments, in_cart,
            in_wishlist, reaction_count, reacted, tab, owned,
            flash=read_flash(request),
        )
    finally:
        conn.close()


# ---- reviews / discussion / wishlist / react --------------------------------

@app.post("/listing/{slug}/review")
def post_review(request: Request, slug: str, rating: int = Form(...),
                body: str = Form(...)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if rating < 1 or rating > 5:
        return flash_redirect(f"/listing/{slug}?tab=reviews", "err",
                              "Rating must be 1–5.")
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return RedirectResponse("/browse", status_code=303)
        conn.execute(
            """INSERT INTO reviews (listing_id, user_id, rating, body)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(listing_id, user_id) DO UPDATE
               SET rating = excluded.rating, body = excluded.body""",
            (row["id"], user["id"], rating, body.strip()),
        )
        recompute_rating(conn, row["id"])
        record_event(conn, "review",
                     f"{user['username']} reviewed {row['title']} — "
                     f"{rating} stars")
        conn.commit()
        return flash_redirect(f"/listing/{slug}?tab=reviews", "ok",
                              "Review posted.")
    finally:
        conn.close()


@app.post("/listing/{slug}/comment")
def post_comment(request: Request, slug: str, body: str = Form(...)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return RedirectResponse("/browse", status_code=303)
        conn.execute(
            "INSERT INTO comments (listing_id, user_id, body) VALUES (?, ?, ?)",
            (row["id"], user["id"], body.strip()),
        )
        conn.commit()
        return flash_redirect(f"/listing/{slug}?tab=discussion", "ok",
                              "Comment posted.")
    finally:
        conn.close()


@app.post("/listing/{slug}/wishlist")
def toggle_wishlist(request: Request, slug: str):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return RedirectResponse("/browse", status_code=303)
        existing = conn.execute(
            "SELECT id FROM wishlist WHERE user_id=? AND listing_id=?",
            (user["id"], row["id"])).fetchone()
        if existing:
            conn.execute("DELETE FROM wishlist WHERE id = ?", (existing["id"],))
            msg = "Removed from wishlist."
        else:
            conn.execute(
                "INSERT INTO wishlist (user_id, listing_id) VALUES (?, ?)",
                (user["id"], row["id"]))
            msg = "Added to wishlist."
        conn.commit()
        return flash_redirect(f"/listing/{slug}", "ok", msg)
    finally:
        conn.close()


@app.post("/listing/{slug}/react")
def toggle_react(request: Request, slug: str):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return RedirectResponse("/browse", status_code=303)
        existing = conn.execute(
            "SELECT id FROM reactions WHERE user_id=? AND listing_id=?",
            (user["id"], row["id"])).fetchone()
        if existing:
            conn.execute("DELETE FROM reactions WHERE id = ?",
                         (existing["id"],))
        else:
            conn.execute(
                "INSERT INTO reactions (listing_id, user_id, emoji) "
                "VALUES (?, ?, '🔥')",
                (row["id"], user["id"]))
        conn.commit()
        return flash_redirect(f"/listing/{slug}", "ok", "Reaction updated.")
    finally:
        conn.close()


@app.post("/listing/{slug}/version")
def upload_version(request: Request, slug: str,
                   version: str = Form(...), changelog: str = Form(...),
                   compile_status: str = Form("pending"),
                   file: UploadFile = File(None)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE slug = ?", (slug,)).fetchone()
        if not row or row["seller_id"] != user["id"]:
            return flash_redirect(f"/listing/{slug}?tab=versions", "err",
                                  "Only the seller can upload a version.")
        if compile_status not in ("passed", "failed", "pending"):
            compile_status = "pending"
        try:
            filename, path, size = save_upload(file)
        except ValueError as e:
            return flash_redirect(f"/listing/{slug}?tab=versions", "err", str(e))
        today = __import__("datetime").date.today().isoformat()
        conn.execute(
            """INSERT INTO versions
               (listing_id, version, changelog, filename, file_path,
                size_bytes, compile_status, compile_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (row["id"], version.strip(), changelog.strip(), filename, path,
             size, compile_status, today if compile_status != "pending" else None),
        )
        conn.execute(
            """UPDATE listings SET version = ?, compile_status = ?,
                   compile_date = ?, updated_at = datetime('now') WHERE id = ?""",
            (version.strip(), compile_status,
             today if compile_status != "pending" else None, row["id"]),
        )
        conn.commit()
        return flash_redirect(f"/listing/{slug}?tab=versions", "ok",
                              f"Version {version} uploaded.")
    finally:
        conn.close()


# ---- auth -------------------------------------------------------------------

def _pepper(password: str) -> str:
    # APP_SECRET_KEY acts as a pepper. Changing it invalidates passwords,
    # so set it once in .env and leave it alone (see README).
    return hashlib.sha256(
        (APP_SECRET_KEY + password).encode()
    ).hexdigest()


@app.get("/signup", response_class=HTMLResponse)
def signup_form(request: Request):
    return templates.auth_page(get_user(request), "signup")


@app.post("/signup")
def signup(request: Request, username: str = Form(...),
           email: str = Form(...), password: str = Form(...)):
    username = username.strip()
    email = email.strip().lower()
    if len(username) < 3 or len(password) < 8 or "@" not in email:
        return HTMLResponse(
            templates.auth_page(
                None, "signup",
                "Username needs 3+ characters, password 8+, valid email."),
            status_code=400,
        )
    conn = connect()
    try:
        existing = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username, email)).fetchone()
        if existing and not existing["is_sample"]:
            return HTMLResponse(
                templates.auth_page(None, "signup",
                                    "That username or email is already taken."),
                status_code=400,
            )
        salt = auth.new_salt()
        pw_hash = auth.hash_password(_pepper(password), salt)
        no_admin_yet = not conn.execute(
            "SELECT 1 FROM users WHERE is_admin = 1").fetchone()
        if existing:
            # Claiming a sample account (e.g. "Realiztik" owns the seeded
            # WeightPlus / AutoWipe_LGSM listings). It becomes a real
            # account; sample flag cleared.
            conn.execute(
                """UPDATE users SET email = ?, password_hash = ?, salt = ?,
                       is_sample = 0, is_admin = ? WHERE id = ?""",
                (email, pw_hash, salt.hex(), 1 if no_admin_yet else 0,
                 existing["id"]),
            )
            user_id = existing["id"]
        else:
            cur = conn.execute(
                """INSERT INTO users (username, email, password_hash, salt,
                                      is_admin)
                   VALUES (?, ?, ?, ?, ?)""",
                (username, email, pw_hash, salt.hex(),
                 1 if no_admin_yet else 0),
            )
            user_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("session_token", auth.create_session(user_id),
                    httponly=True, samesite="lax", max_age=30 * 86400)
    return resp


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.auth_page(get_user(request), "login")


@app.post("/login")
def login(request: Request, username: str = Form(...),
          password: str = Form(...)):
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
        if not row or not auth.verify_password(
            _pepper(password), row["salt"], row["password_hash"]
        ):
            return HTMLResponse(
                templates.auth_page(None, "login",
                                    "Wrong username or password."),
                status_code=400,
            )
        user_id = row["id"]
    finally:
        conn.close()
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("session_token", auth.create_session(user_id),
                    httponly=True, samesite="lax", max_age=30 * 86400)
    return resp


@app.get("/logout")
def logout(request: Request):
    auth.destroy_session(request.cookies.get("session_token"))
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie("session_token")
    return resp


# ---- sell -------------------------------------------------------------------

@app.get("/sell", response_class=HTMLResponse)
def sell_form(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.sell_page(user)


@app.post("/sell")
def sell(request: Request, title: str = Form(...),
         description: str = Form(...), category: str = Form(...),
         price: float = Form(0), version: str = Form("1.0.0"),
         compatibility: str = Form("Oxide"), docs: str = Form(""),
         license_text: str = Form(""), support_text: str = Form(""),
         game: str = Form("rust"),
         is_wip: str = Form(None), file: UploadFile = File(None)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if category not in templates.CATEGORIES:
        return HTMLResponse(
            templates.sell_page(user, "Pick a valid category."),
            status_code=400)
    if game not in [g[0] for g in GAMES]:
        game = "rust"
    if not license_text.strip():
        # RogueDepot-style per-listing licence: use on any number of
        # your servers, no redistribution, resale or sharing.
        license_text = DEFAULT_LICENSE_TEXT
    conn = connect()
    try:
        try:
            filename, path, size = save_upload(file)
        except ValueError as e:
            return HTMLResponse(templates.sell_page(user, str(e)),
                                status_code=400)
        slug = unique_slug(conn, title)
        today = __import__("datetime").date.today().isoformat()
        cur = conn.execute(
            """INSERT INTO listings
               (title, slug, description, docs, license_text, support_text,
                price_cents, category, game, version, compatibility, seller_id,
                status, is_wip)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (title.strip(), slug, description.strip(), docs.strip(),
             license_text.strip(), support_text.strip(),
             int(round(price * 100)), category, game, version.strip(),
             compatibility, user["id"], 1 if is_wip else 0),
        )
        listing_id = cur.lastrowid
        conn.execute(
            """INSERT INTO versions
               (listing_id, version, changelog, filename, file_path,
                size_bytes, compile_status, compile_date)
               VALUES (?, ?, 'Initial release.', ?, ?, ?, 'pending', NULL)""",
            (listing_id, version.strip(), filename, path, size),
        )
        record_event(conn, "published",
                     f"{user['username']} submitted {title} for review")
        conn.commit()
        return flash_redirect(
            "/account", "ok",
            "Listing submitted — it is in the review queue and will go live "
            "once an admin approves it.")
    finally:
        conn.close()


# ---- cart + demo checkout ----------------------------------------------------

@app.get("/cart", response_class=HTMLResponse)
def cart(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        items = [dict(r) for r in conn.execute(
            """SELECT l.* FROM cart_items c JOIN listings l ON l.id = c.listing_id
               WHERE c.user_id = ? ORDER BY c.id""", (user["id"],))]
        total = sum(i["price_cents"] for i in items)
        return templates.cart_page(user, items, total,
                                   paypal_pay.paypal_enabled(),
                                   flash=read_flash(request))
    finally:
        conn.close()


@app.post("/cart/add/{listing_id}")
def cart_add(request: Request, listing_id: int):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE id = ? AND status = 'approved'",
            (listing_id,)).fetchone()
        if not row:
            return RedirectResponse("/browse", status_code=303)
        if has_purchase(conn, user["id"], listing_id):
            return flash_redirect(f"/listing/{row['slug']}", "ok",
                                  "You already own this listing.")
        conn.execute(
            """INSERT OR IGNORE INTO cart_items (user_id, listing_id)
               VALUES (?, ?)""", (user["id"], listing_id))
        conn.commit()
        return RedirectResponse("/cart", status_code=303)
    finally:
        conn.close()


@app.post("/cart/remove/{listing_id}")
def cart_remove(request: Request, listing_id: int):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        conn.execute(
            "DELETE FROM cart_items WHERE user_id = ? AND listing_id = ?",
            (user["id"], listing_id))
        conn.commit()
        return RedirectResponse("/cart", status_code=303)
    finally:
        conn.close()


# ---- purchases, commission split + payout ledger ---------------------------

def record_purchase(conn, user_id: int, listing: dict, demo: bool,
                    paypal_order_id: str | None = None,
                    paypal_capture_id: str | None = None) -> dict | None:
    """Insert a purchase row (idempotent per user+listing for non-refunded
    purchases) and return it as a dict. Returns None if the user already
    owns the listing.

    Paid, non-demo sales record the 15% / 85% split on the purchase and
    in the payouts ledger (the platform's record of the instant PayPal
    payout). Free/demo purchases have no split. There are no licence
    keys any more — buyers get download access from their library,
    RogueDepot-style.
    """
    if has_purchase(conn, user_id, listing["id"]):
        return None
    fee_cents, seller_cents = (0, 0)
    if listing["price_cents"] > 0 and not demo:
        fee_cents, seller_cents = split_cents(listing["price_cents"])
    cur = conn.execute(
        """INSERT INTO purchases
           (user_id, listing_id, amount_cents, demo, platform_fee_cents,
            seller_amount_cents, paypal_order_id, paypal_capture_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, listing["id"], listing["price_cents"],
         1 if demo else 0, fee_cents, seller_cents,
         paypal_order_id, paypal_capture_id),
    )
    purchase_id = cur.lastrowid
    if listing["price_cents"] > 0 and not demo:
        conn.execute(
            """INSERT INTO payouts
               (purchase_id, seller_id, listing_id, gross_cents,
                platform_fee_cents, seller_cents, paypal_order_id,
                paypal_capture_id, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'paid')""",
            (purchase_id, listing["seller_id"], listing["id"],
             listing["price_cents"], fee_cents, seller_cents,
             paypal_order_id, paypal_capture_id),
        )
    conn.execute(
        "UPDATE listings SET purchases_count = purchases_count + 1,"
        " downloads = downloads + 1 WHERE id = ?",
        (listing["id"],),
    )
    buyer = conn.execute(
        "SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    record_event(conn, "purchase",
                 f"{buyer['username'] if buyer else 'A buyer'} purchased "
                 f"{listing['title']}")
    return {
        "id": purchase_id,
        "user_id": user_id,
        "listing_id": listing["id"],
        "title": listing["title"],
        "slug": listing["slug"],
        "amount_cents": listing["price_cents"],
        "platform_fee_cents": fee_cents,
        "seller_amount_cents": seller_cents,
        "paypal_order_id": paypal_order_id,
        "paypal_capture_id": paypal_capture_id,
        "demo": demo,
    }


def notify_sale(conn, listing: dict, buyer_username: str,
                fee_cents: int = 0, seller_cents: int = 0) -> None:
    """Best-effort email to the seller about a new sale (no-op without
    SMTP configured)."""
    seller = conn.execute(
        "SELECT email FROM users WHERE id = ?", (listing["seller_id"],)
    ).fetchone()
    if seller and seller["email"]:
        body = (
            f"Hi,\n\n{buyer_username} just bought your listing "
            f"'{listing['title']}' for "
            f"${listing['price_cents'] / 100:,.2f} via PayPal.\n"
        )
        if fee_cents or seller_cents:
            body += (
                f"\nYour share (85%): ${seller_cents / 100:,.2f}, paid "
                f"instantly to your connected PayPal account. Platform "
                f"fee (15%): ${fee_cents / 100:,.2f}.\n"
            )
        body += ("\nSee your seller dashboard for the details."
                 "\n\n— The Rusting Dead Mod Marketplace")
        mail.send(
            seller["email"],
            f"New sale: {listing['title']}",
            body,
        )


# ---- cart + checkout (PayPal Commerce when configured) --------------------

def _finalise_paypal_purchase(conn, user_id: int, unit: dict,
                              order_id: str) -> dict | None:
    """Record one captured PayPal purchase unit. unit is one entry from
    paypal_pay.parse_captured_units(). Idempotent: returns None if the
    buyer already owns the listing (e.g. the success redirect recorded
    it and the webhook fires later). Also removes the item from the
    buyer's cart."""
    row = conn.execute(
        "SELECT * FROM listings WHERE id = ?", (unit["listing_id"],)
    ).fetchone()
    if not row:
        return None
    bought = record_purchase(
        conn, user_id, dict(row), demo=False,
        paypal_order_id=order_id,
        paypal_capture_id=unit["capture_id"],
    )
    if bought:
        buyer = conn.execute(
            "SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        notify_sale(conn, dict(row),
                    buyer["username"] if buyer else "a buyer",
                    bought["platform_fee_cents"],
                    bought["seller_amount_cents"])
        conn.execute(
            "DELETE FROM cart_items WHERE user_id = ? AND listing_id = ?",
            (user_id, row["id"]))
    return bought


@app.post("/checkout")
def checkout(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        items = [dict(r) for r in conn.execute(
            """SELECT l.* FROM cart_items c JOIN listings l ON l.id = c.listing_id
               WHERE c.user_id = ?""", (user["id"],))]
        if not items:
            return RedirectResponse("/cart", status_code=303)
        free_items = [i for i in items if i["price_cents"] == 0]
        paid_items = [i for i in items if i["price_cents"] > 0]
        # Free items always complete immediately, no payment involved.
        for item in free_items:
            record_purchase(conn, user["id"], item, demo=True)
            conn.execute(
                "DELETE FROM cart_items WHERE user_id = ? AND listing_id = ?",
                (user["id"], item["id"]))
        conn.commit()
        if not paid_items:
            return flash_redirect(
                "/account", "ok",
                "Checkout complete — your free listings are in My purchases "
                "and ready to download.")
        if not paypal_pay.paypal_enabled():
            # Payments are not configured: keep the paid items in the cart
            # and say so plainly. Free items (if any) were already recorded.
            conn.commit()
            return flash_redirect(
                "/cart", "err",
                "Payments are not configured yet — the site owner needs to "
                "set PayPal keys in .env before paid checkout works. "
                "Free items were completed; paid items are still in your cart.")
        # One PayPal order: one purchase unit per paid item, each paying
        # its seller with INSTANT disbursement and the 15% platform fee.
        units = []
        for item in paid_items:
            seller = conn.execute(
                "SELECT paypal_merchant_id FROM users WHERE id = ?",
                (item["seller_id"],)).fetchone()
            merchant_id = (seller["paypal_merchant_id"] or "") if seller else ""
            if not merchant_id:
                conn.commit()
                return flash_redirect(
                    "/cart", "err",
                    f"The seller of '{item['title']}' has not connected a "
                    "PayPal account for payouts yet, so it cannot be sold "
                    "through PayPal right now. Paid items are still in "
                    "your cart.")
            fee_cents, _ = split_cents(item["price_cents"])
            units.append({
                "listing_id": item["id"],
                "title": item["title"],
                "amount_cents": item["price_cents"],
                "fee_cents": fee_cents,
                "seller_merchant_id": merchant_id,
            })
        try:
            order = paypal_pay.create_order(
                user["id"], units,
                f"{BASE_URL}/checkout/paypal/success",
                f"{BASE_URL}/checkout/paypal/cancel",
            )
        except paypal_pay.PayPalError as e:
            conn.commit()
            return flash_redirect(
                "/cart", "err",
                f"PayPal checkout could not be started: {e} "
                "Your cart is unchanged.")
        url = paypal_pay.approval_url(order)
        if not url:
            conn.commit()
            return flash_redirect(
                "/cart", "err",
                "PayPal did not return an approval link — your cart is "
                "unchanged.")
        conn.commit()
        return RedirectResponse(url, status_code=303)
    finally:
        conn.close()


@app.get("/checkout/paypal/success", response_class=HTMLResponse)
def paypal_success(request: Request, token: str = ""):
    """PayPal redirects the buyer here after approval, with
    ?token=<order id>. Capture the order and record the purchases."""
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if not token:
        return RedirectResponse("/account", status_code=303)
    conn = connect()
    try:
        try:
            order = paypal_pay.capture_order(token)
        except paypal_pay.PayPalError as e:
            return flash_redirect(
                "/cart", "err",
                f"PayPal capture failed: {e} No purchase was recorded.")
        bought = []
        for unit in paypal_pay.parse_captured_units(order):
            if unit["user_id"] != user["id"]:
                continue
            done = _finalise_paypal_purchase(conn, user["id"], unit, token)
            if done:
                bought.append(done)
        conn.commit()
        return templates.checkout_success_page(user, bought)
    finally:
        conn.close()


@app.get("/checkout/paypal/cancel", response_class=HTMLResponse)
def paypal_cancel(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return flash_redirect(
        "/cart", "err",
        "PayPal checkout was cancelled — nothing was charged and your "
        "cart is unchanged.")


@app.post("/paypal/webhook")
async def paypal_webhook(request: Request):
    """PayPal webhook: verifies the signature against PayPal's API and,
    on PAYMENT.CAPTURE.COMPLETED, finalises any purchases the success
    redirect missed. Returns 400 for anything unverified or
    unconfigured — an unverified endpoint accepts a POST from anyone,
    not just PayPal."""
    if not paypal_pay.paypal_enabled():
        return HTMLResponse("paypal not configured", status_code=400)
    raw = await request.body()
    try:
        verified = paypal_pay.verify_webhook(request.headers, raw)
    except paypal_pay.PayPalError:
        return HTMLResponse("verification error", status_code=400)
    if not verified:
        return HTMLResponse("bad signature", status_code=400)
    try:
        event = json.loads(raw.decode("utf-8"))
    except Exception:
        return HTMLResponse("bad payload", status_code=400)
    if event.get("event_type") == "PAYMENT.CAPTURE.COMPLETED":
        resource = event.get("resource", {})
        order_id = ((resource.get("supplementary_data") or {})
                    .get("related_ids") or {}).get("order_id")
        if order_id:
            conn = connect()
            try:
                try:
                    order = paypal_pay.get_order(order_id)
                except paypal_pay.PayPalError:
                    return HTMLResponse("ok")
                for unit in paypal_pay.parse_captured_units(order):
                    _finalise_paypal_purchase(conn, unit["user_id"], unit,
                                              order_id)
                conn.commit()
            finally:
                conn.close()
    return HTMLResponse("ok")


# ---- downloads ----------------------------------------------------------------

@app.get("/download/{slug}")
def download_listing(request: Request, slug: str):
    user = get_user(request)
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE slug = ? AND status = 'approved'",
            (slug,)).fetchone()
        if not row:
            return RedirectResponse("/browse", status_code=303)
        listing = dict(row)
        if listing["price_cents"] > 0:
            if not user:
                return RedirectResponse("/login", status_code=303)
            if (user["id"] != listing["seller_id"]
                    and not has_purchase(conn, user["id"], listing["id"])):
                return flash_redirect(
                    f"/listing/{slug}", "err",
                    "Buy this listing first — it is in your cart after checkout.")
        version = conn.execute(
            """SELECT * FROM versions WHERE listing_id = ? AND file_path IS NOT NULL
               ORDER BY id DESC LIMIT 1""", (listing["id"],)).fetchone()
        if not version:
            return flash_redirect(
                f"/listing/{slug}?tab=versions", "err",
                "No downloadable file attached to this listing yet.")
        conn.execute(
            "UPDATE listings SET downloads = downloads + 1 WHERE id = ?",
            (listing["id"],))
        record_event(conn, "download",
                     f"{user['username'] if user else 'Guest'} downloaded "
                     f"{listing['title']}")
        conn.commit()
        return FileResponse(version["file_path"],
                            filename=version["filename"] or "download")
    finally:
        conn.close()


@app.get("/download/version/{version_id}")
def download_version(request: Request, version_id: int):
    user = get_user(request)
    conn = connect()
    try:
        version = conn.execute(
            "SELECT * FROM versions WHERE id = ?", (version_id,)).fetchone()
        if not version or not version["file_path"]:
            return RedirectResponse("/browse", status_code=303)
        listing = conn.execute(
            "SELECT * FROM listings WHERE id = ?",
            (version["listing_id"],)).fetchone()
        if listing["price_cents"] > 0:
            if not user:
                return RedirectResponse("/login", status_code=303)
            if (user["id"] != listing["seller_id"]
                    and not has_purchase(conn, user["id"], listing["id"])):
                return flash_redirect(
                    f"/listing/{listing['slug']}?tab=versions", "err",
                    "Buy this listing first.")
        conn.execute(
            "UPDATE listings SET downloads = downloads + 1 WHERE id = ?",
            (listing["id"],))
        conn.commit()
        return FileResponse(version["file_path"],
                            filename=version["filename"] or "download")
    finally:
        conn.close()


# ---- account ------------------------------------------------------------------

@app.get("/account", response_class=HTMLResponse)
def account(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        mine = [dict(r) for r in conn.execute(
            "SELECT * FROM listings WHERE seller_id = ? ORDER BY id DESC",
            (user["id"],))]
        purchases = [dict(r) for r in conn.execute(
            """SELECT p.*, l.slug, l.title FROM purchases p
               JOIN listings l ON l.id = p.listing_id
               WHERE p.user_id = ? ORDER BY p.id DESC""", (user["id"],))]
        wishlist_items = [dict(r) for r in conn.execute(
            """SELECT l.* FROM wishlist w JOIN listings l ON l.id = w.listing_id
               WHERE w.user_id = ? ORDER BY w.id DESC""", (user["id"],))]
        return templates.account_page(user, mine, purchases,
                                     wishlist_items,
                                     flash=read_flash(request))
    finally:
        conn.close()


# ---- author pages -------------------------------------------------------------

@app.get("/author/{username}", response_class=HTMLResponse)
def author_page_route(request: Request, username: str):
    """Public author page: bio + their live listings, each carrying its
    game (Rust now; other games later)."""
    user = get_user(request)
    conn = connect()
    try:
        author = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not author:
            return HTMLResponse(
                templates.layout("Not found", user,
                                 "<div class='wrap'><div class='section'>"
                                 "<h2>Author not found</h2></div></div>"),
                status_code=404)
        listings = [dict(r) for r in conn.execute(
            "SELECT * FROM listings WHERE seller_id = ? AND status = 'approved'"
            " ORDER BY created_at DESC, id DESC",
            (author["id"],))]
        return templates.author_page(user, dict(author), listings)
    finally:
        conn.close()


# ---- admin --------------------------------------------------------------------

def require_admin(request: Request):
    user = get_user(request)
    if not user or not user["is_admin"]:
        return None
    return user


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    user = require_admin(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        queue = [dict(r) for r in conn.execute(
            """SELECT l.*, u.username AS seller FROM listings l
               JOIN users u ON u.id = l.seller_id
               WHERE l.status IN ('pending', 'flagged')
               ORDER BY l.id ASC""")]
        users = [dict(r) for r in conn.execute(
            "SELECT * FROM users ORDER BY id ASC")]
        sales = [dict(r) for r in conn.execute(
            """SELECT p.*, l.slug, l.title, u.username AS buyer
               FROM purchases p JOIN listings l ON l.id = p.listing_id
               JOIN users u ON u.id = p.user_id ORDER BY p.id DESC LIMIT 50""")]
        fee_totals = conn.execute(
            """SELECT COALESCE(SUM(platform_fee_cents), 0) AS fees,
                      COALESCE(SUM(seller_amount_cents), 0) AS sellers,
                      COALESCE(SUM(amount_cents), 0) AS gross
               FROM purchases WHERE demo = 0 AND refunded = 0"""
        ).fetchone()
        reports = [dict(r) for r in conn.execute(
            """SELECT r.*, l.title AS listing_title, l.slug AS listing_slug,
                      u.username AS reported_user,
                      rep.username AS reporter
               FROM reports r
               LEFT JOIN listings l ON l.id = r.listing_id
               LEFT JOIN users u ON u.id = r.reported_user_id
               JOIN users rep ON rep.id = r.reporter_id
               WHERE r.status = 'open' ORDER BY r.id ASC""")]
        settings = get_settings(conn)
        return templates.admin_page(
            user, queue, users, sales, settings, reports,
            totals={
                "fees": fee_totals["fees"],
                "sellers": fee_totals["sellers"],
                "gross": fee_totals["gross"],
            })
    finally:
        conn.close()


@app.post("/admin/approve/{listing_id}")
def admin_approve(request: Request, listing_id: int):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE listings SET status = 'approved', review_note = ''"
                " WHERE id = ?",
                (listing_id,))
            record_event(conn, "approved", f"Admin approved {row['title']}")
            conn.commit()
            seller = conn.execute(
                "SELECT email FROM users WHERE id = ?",
                (row["seller_id"],)).fetchone()
            if seller and seller["email"]:
                mail.send(
                    seller["email"],
                    f"Your listing was approved: {row['title']}",
                    f"Hi,\n\nGood news — your listing '{row['title']}' "
                    f"has been approved and is now live on The Rusting Dead Mod Marketplace.\n\n"
                    f"— The Rusting Dead Mod Marketplace",
                )
        return RedirectResponse("/admin", status_code=303)
    finally:
        conn.close()


@app.post("/admin/flag/{listing_id}")
def admin_flag(request: Request, listing_id: int,
               reason: str = Form("")):
    """Flag a listing for human review (RogueDepot wording: typically
    24–48 hours). The seller is emailed the reason."""
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    reason = reason.strip() or "Needs a closer look before it can go live."
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE listings SET status = 'flagged', review_note = ?"
                " WHERE id = ?",
                (reason, listing_id))
            record_event(conn, "flagged",
                         f"Admin flagged {row['title']} for review: {reason}")
            conn.commit()
            seller = conn.execute(
                "SELECT email FROM users WHERE id = ?",
                (row["seller_id"],)).fetchone()
            if seller and seller["email"]:
                mail.send(
                    seller["email"],
                    f"Your listing was flagged for review: {row['title']}",
                    f"Hi,\n\nYour listing '{row['title']}' was flagged "
                    f"for a closer human review (typically 24–48 hours).\n\n"
                    f"Reason: {reason}\n\nYou can fix the listing and "
                    f"it will be reviewed again, or open a support ticket "
                    f"if you think this was a mistake.\n\n— The Rusting Dead Mod Marketplace",
                )
        return RedirectResponse("/admin", status_code=303)
    finally:
        conn.close()


@app.post("/admin/reject/{listing_id}")
def admin_reject(request: Request, listing_id: int,
                 reason: str = Form("")):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    reason = reason.strip()
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE listings SET status = 'rejected', review_note = ?"
                " WHERE id = ?",
                (reason, listing_id))
            conn.commit()
            seller = conn.execute(
                "SELECT email FROM users WHERE id = ?",
                (row["seller_id"],)).fetchone()
            if seller and seller["email"]:
                body = (
                    f"Hi,\n\nYour listing '{row['title']}' was reviewed "
                    f"and not approved."
                )
                if reason:
                    body += f"\n\nReason: {reason}"
                body += (
                    "\n\nYou can edit it and submit it again, or open a "
                    "support ticket if you think this was a mistake.\n\n"
                    "— The Rusting Dead Mod Marketplace"
                )
                mail.send(
                    seller["email"],
                    f"Your listing was not approved: {row['title']}",
                    body,
                )
        return RedirectResponse("/admin", status_code=303)
    finally:
        conn.close()


@app.post("/admin/settings")
def admin_settings(request: Request,
                   discord_invite_url: str = Form(""),
                   discord_online: str = Form("0"),
                   discord_members: str = Form("0")):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        for key, value in (
            ("discord_invite_url", discord_invite_url.strip()),
            ("discord_online", discord_online.strip()),
            ("discord_members", discord_members.strip()),
        ):
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
        conn.commit()
        return RedirectResponse("/admin", status_code=303)
    finally:
        conn.close()


# ---- password reset ---------------------------------------------------------

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_form(request: Request):
    return templates.forgot_page(get_user(request))


@app.post("/forgot-password", response_class=HTMLResponse)
def forgot_submit(request: Request, identifier: str = Form(...)):
    identifier = identifier.strip().lower()
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE lower(email) = ? OR lower(username) = ?",
            (identifier, identifier)).fetchone()
        dev_link = None
        if row and not row["is_sample"]:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
            conn.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at)"
                " VALUES (?, ?, ?)",
                (row["id"], token_hash, expires))
            conn.commit()
            link = f"{BASE_URL}/reset-password?token={token}"
            if mail.smtp_configured():
                mail.send(
                    row["email"], "Reset your password — The Rusting Dead Mod Marketplace",
                    f"Hi {row['username']},\n\nReset your password here "
                    f"(valid 1 hour):\n{link}\n\nIf you didn't ask for "
                    f"this, ignore this email.\n\n— The Rusting Dead Mod Marketplace")
            else:
                # No SMTP: show the link on screen to the requester only,
                # clearly labelled as dev mode. Never log it, never email it.
                dev_link = link
        return templates.forgot_page(get_user(request), sent=True,
                                     dev_link=dev_link)
    finally:
        conn.close()


@app.get("/reset-password", response_class=HTMLResponse)
def reset_form(request: Request, token: str = ""):
    return templates.reset_page(get_user(request), token)


@app.post("/reset-password", response_class=HTMLResponse)
def reset_submit(request: Request, token: str = Form(...),
                 password: str = Form(...)):
    if len(password) < 8:
        return HTMLResponse(
            templates.reset_page(get_user(request), token,
                                 "Password needs 8+ characters."),
            status_code=400)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM password_resets WHERE token_hash = ? AND used = 0"
            " AND expires_at > datetime('now')",
            (token_hash,)).fetchone()
        if not row:
            return HTMLResponse(
                templates.reset_page(
                    get_user(request), token,
                    "That reset link is invalid or expired."),
                status_code=400)
        salt = auth.new_salt()
        pw_hash = auth.hash_password(_pepper(password), salt)
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
            (pw_hash, salt.hex(), row["user_id"]))
        conn.execute("UPDATE password_resets SET used = 1 WHERE id = ?",
                     (row["id"],))
        conn.execute("DELETE FROM sessions WHERE user_id = ?",
                     (row["user_id"],))
        conn.commit()
        return templates.auth_page(
            None, "login",
            notice="Password reset — sign in with your new password.")
    finally:
        conn.close()


# ---- support tickets ----------------------------------------------------------

TICKET_STATUSES = ("open", "awaiting-seller", "awaiting-buyer", "resolved",
                   "closed")


def _can_view_ticket(user: dict, ticket: dict) -> bool:
    if user["is_admin"]:
        return True
    return (ticket["buyer_id"] == user["id"]
            or (ticket["seller_id"]
                and ticket["seller_id"] == user["id"]))


def _ticket_other_party(conn, user: dict, ticket: dict):
    """Return the user row that should be emailed on a new reply."""
    if user["id"] == ticket["buyer_id"] and ticket["seller_id"]:
        return conn.execute("SELECT * FROM users WHERE id = ?",
                            (ticket["seller_id"],)).fetchone()
    if ticket["seller_id"] and user["id"] == ticket["seller_id"]:
        return conn.execute("SELECT * FROM users WHERE id = ?",
                            (ticket["buyer_id"],)).fetchone()
    return None


@app.get("/tickets", response_class=HTMLResponse)
def ticket_list(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        if user["is_admin"]:
            rows = conn.execute(
                """SELECT t.*, l.title AS listing_title,
                          b.username AS buyer, s.username AS seller
                   FROM tickets t
                   LEFT JOIN listings l ON l.id = t.listing_id
                   JOIN users b ON b.id = t.buyer_id
                   LEFT JOIN users s ON s.id = t.seller_id
                   ORDER BY t.updated_at DESC, t.id DESC"""
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT t.*, l.title AS listing_title,
                          b.username AS buyer, s.username AS seller
                   FROM tickets t
                   LEFT JOIN listings l ON l.id = t.listing_id
                   JOIN users b ON b.id = t.buyer_id
                   LEFT JOIN users s ON s.id = t.seller_id
                   WHERE t.buyer_id = ? OR t.seller_id = ?
                   ORDER BY t.updated_at DESC, t.id DESC""",
                (user["id"], user["id"])).fetchall()
        return templates.tickets_page(user, [dict(r) for r in rows],
                                      flash=read_flash(request))
    finally:
        conn.close()


@app.get("/tickets/new", response_class=HTMLResponse)
def ticket_new_form(request: Request, listing: str = ""):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        listing_row = None
        if listing:
            row = conn.execute(
                "SELECT * FROM listings WHERE slug = ? AND status = 'approved'",
                (listing,)).fetchone()
            listing_row = dict(row) if row else None
        return templates.new_ticket_page(user, listing_row)
    finally:
        conn.close()


@app.post("/tickets/new")
def ticket_create(request: Request, subject: str = Form(...),
                  body: str = Form(...),
                  listing_id: int = Form(0)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        listing = None
        seller_id = None
        if listing_id:
            row = conn.execute(
                "SELECT * FROM listings WHERE id = ? AND status = 'approved'",
                (listing_id,)).fetchone()
            if row:
                listing = dict(row)
                seller_id = row["seller_id"]
        cur = conn.execute(
            """INSERT INTO tickets (listing_id, buyer_id, seller_id, subject)
               VALUES (?, ?, ?, ?)""",
            (listing["id"] if listing else None, user["id"], seller_id,
             subject.strip()))
        ticket_id = cur.lastrowid
        conn.execute(
            "INSERT INTO ticket_replies (ticket_id, user_id, body)"
            " VALUES (?, ?, ?)",
            (ticket_id, user["id"], body.strip()))
        conn.commit()
        if seller_id:
            seller = conn.execute("SELECT * FROM users WHERE id = ?",
                                  (seller_id,)).fetchone()
            if seller and seller["email"]:
                mail.send(
                    seller["email"],
                    f"New support ticket: {subject.strip()}",
                    f"Hi {seller['username']},\n\n{user['username']} opened "
                    f"a support ticket"
                    + (f" about your listing '{listing['title']}'" if listing else "")
                    + f":\n\n{body.strip()}\n\nReply from your ticket list "
                    f"on The Rusting Dead Mod Marketplace.\n\n— The Rusting Dead Mod Marketplace")
        return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)
    finally:
        conn.close()


@app.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail(request: Request, ticket_id: int):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute(
            """SELECT t.*, l.title AS listing_title, l.slug AS listing_slug,
                      b.username AS buyer, s.username AS seller
               FROM tickets t
               LEFT JOIN listings l ON l.id = t.listing_id
               JOIN users b ON b.id = t.buyer_id
               LEFT JOIN users s ON s.id = t.seller_id
               WHERE t.id = ?""",
            (ticket_id,)).fetchone()
        if not row or not _can_view_ticket(user, dict(row)):
            return HTMLResponse(
                templates.layout("Not found", user,
                                 "<div class='wrap'><div class='section'>"
                                 "<h2>Ticket not found</h2></div></div>"),
                status_code=404)
        ticket = dict(row)
        replies = [dict(r) for r in conn.execute(
            """SELECT r.*, u.username FROM ticket_replies r
               JOIN users u ON u.id = r.user_id
               WHERE r.ticket_id = ? ORDER BY r.id ASC""",
            (ticket_id,))]
        return templates.ticket_detail_page(user, ticket, replies,
                                            flash=read_flash(request))
    finally:
        conn.close()


@app.post("/tickets/{ticket_id}/reply")
def ticket_reply(request: Request, ticket_id: int, body: str = Form(...)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?",
                           (ticket_id,)).fetchone()
        if not row or not _can_view_ticket(user, dict(row)):
            return RedirectResponse("/tickets", status_code=303)
        ticket = dict(row)
        conn.execute(
            "INSERT INTO ticket_replies (ticket_id, user_id, body)"
            " VALUES (?, ?, ?)",
            (ticket_id, user["id"], body.strip()))
        if ticket["status"] in ("resolved", "closed"):
            new_status = "open"
        elif user["id"] == ticket["buyer_id"]:
            new_status = "awaiting-seller"
        else:
            new_status = "awaiting-buyer"
        conn.execute(
            "UPDATE tickets SET status = ?, updated_at = datetime('now')"
            " WHERE id = ?",
            (new_status, ticket_id))
        conn.commit()
        other = _ticket_other_party(conn, user, ticket)
        if other and other["email"]:
            mail.send(
                other["email"],
                f"Reply on ticket #{ticket_id}: {ticket['subject']}",
                f"Hi {other['username']},\n\n{user['username']} replied "
                f"to support ticket #{ticket_id} "
                f"('{ticket['subject']}'):\n\n{body.strip()}\n\n"
                f"Reply from your ticket list on The Rusting Dead Mod Marketplace.\n\n— The Rusting Dead Mod Marketplace")
        return flash_redirect(f"/tickets/{ticket_id}", "ok", "Reply posted.")
    finally:
        conn.close()


@app.post("/tickets/{ticket_id}/status")
def ticket_set_status(request: Request, ticket_id: int,
                      status: str = Form(...)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if status not in TICKET_STATUSES:
        return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?",
                           (ticket_id,)).fetchone()
        if not row or not _can_view_ticket(user, dict(row)):
            return RedirectResponse("/tickets", status_code=303)
        conn.execute(
            "UPDATE tickets SET status = ?, updated_at = datetime('now')"
            " WHERE id = ?",
            (status, ticket_id))
        conn.commit()
        return flash_redirect(f"/tickets/{ticket_id}", "ok",
                              f"Ticket marked {status}.")
    finally:
        conn.close()


# ---- reporting + moderation ---------------------------------------------------

REPORT_REASONS = ("Spam", "Scam / fraud", "Stolen content", "Malware",
                  "Offensive content", "Other")


@app.get("/listing/{slug}/report", response_class=HTMLResponse)
def report_form(request: Request, slug: str):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return RedirectResponse("/browse", status_code=303)
        return templates.report_page(user, dict(row))
    finally:
        conn.close()


@app.post("/listing/{slug}/report")
def report_submit(request: Request, slug: str,
                  target: str = Form("listing"),
                  reason: str = Form(...), body: str = Form("")):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if reason not in REPORT_REASONS:
        reason = "Other"
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM listings WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return RedirectResponse("/browse", status_code=303)
        if target == "seller":
            conn.execute(
                """INSERT INTO reports
                   (reporter_id, listing_id, reported_user_id, reason, body)
                   VALUES (?, NULL, ?, ?, ?)""",
                (user["id"], row["seller_id"], reason, body.strip()))
        else:
            conn.execute(
                """INSERT INTO reports
                   (reporter_id, listing_id, reported_user_id, reason, body)
                   VALUES (?, ?, ?, ?, ?)""",
                (user["id"], row["id"], row["seller_id"], reason,
                 body.strip()))
        conn.commit()
        return flash_redirect(f"/listing/{slug}", "ok",
                              "Report sent — an admin will review it.")
    finally:
        conn.close()


@app.post("/admin/reports/{report_id}/dismiss")
def report_dismiss(request: Request, report_id: int):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        conn.execute("UPDATE reports SET status = 'dismissed' WHERE id = ?",
                     (report_id,))
        conn.commit()
        return RedirectResponse("/admin", status_code=303)
    finally:
        conn.close()


@app.post("/admin/reports/{report_id}/hide")
def report_hide(request: Request, report_id: int):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM reports WHERE id = ?",
                           (report_id,)).fetchone()
        if row and row["listing_id"]:
            conn.execute(
                "UPDATE listings SET status = 'hidden' WHERE id = ?",
                (row["listing_id"],))
        conn.execute("UPDATE reports SET status = 'actioned' WHERE id = ?",
                     (report_id,))
        conn.commit()
        return RedirectResponse("/admin", status_code=303)
    finally:
        conn.close()


# ---- refunds ------------------------------------------------------------------

def issue_refund(conn, purchase_id: int) -> tuple[bool, str]:
    """Refund a paid purchase and revoke the buyer's download access.

    If the purchase has a PayPal capture id and PayPal is configured,
    the refund is issued through PayPal first — if that fails, nothing
    is changed locally (the buyer was not actually refunded). Demo and
    free purchases never moved real money, so they are refunded locally
    only. The payout ledger row flips to 'refunded' and the buyer is
    emailed. Returns (ok, message).
    """
    row = conn.execute(
        "SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
    if not row:
        return False, "Purchase not found."
    purchase = dict(row)
    if purchase["refunded"]:
        return False, "This purchase was already refunded."
    if purchase["amount_cents"] <= 0:
        return False, "Free purchases have nothing to refund."
    if purchase["paypal_capture_id"] and paypal_pay.paypal_enabled():
        try:
            paypal_pay.refund_capture(purchase["paypal_capture_id"],
                                      purchase["amount_cents"])
        except paypal_pay.PayPalError as e:
            return False, f"PayPal refund failed: {e} Nothing was changed."
    listing = conn.execute(
        "SELECT * FROM listings WHERE id = ?", (purchase["listing_id"],)
    ).fetchone()
    title = listing["title"] if listing else "a listing"
    conn.execute(
        "UPDATE purchases SET refunded = 1, refunded_at = datetime('now')"
        " WHERE id = ?",
        (purchase_id,))
    conn.execute(
        "UPDATE payouts SET status = 'refunded' WHERE purchase_id = ?",
        (purchase_id,))
    record_event(conn, "refund",
                 f"Refunded purchase of {title} "
                 f"(${purchase['amount_cents'] / 100:,.2f}) — download "
                 f"access revoked.")
    conn.commit()
    buyer = conn.execute(
        "SELECT email, username FROM users WHERE id = ?",
        (purchase["user_id"],)).fetchone()
    if buyer and buyer["email"]:
        mail.send(
            buyer["email"],
            f"Refund issued: {title}",
            f"Hi {buyer['username']},\n\nYour purchase of '{title}' "
            f"(${purchase['amount_cents'] / 100:,.2f}) has been refunded. "
            f"Your download access to it has been revoked.\n\n"
            f"If you did not ask for this, open a support ticket.\n\n"
            f"— The Rusting Dead Mod Marketplace",
        )
    return True, "Refund issued — the buyer's download access is revoked."


@app.post("/seller/refund/{purchase_id}")
def seller_refund(request: Request, purchase_id: int):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute(
            """SELECT p.* FROM purchases p JOIN listings l
               ON l.id = p.listing_id
               WHERE p.id = ? AND l.seller_id = ?""",
            (purchase_id, user["id"])).fetchone()
        if not row:
            return flash_redirect("/seller", "err",
                                  "That sale is not yours to refund.")
        ok, msg = issue_refund(conn, purchase_id)
        return flash_redirect("/seller", "ok" if ok else "err", msg)
    finally:
        conn.close()


@app.post("/admin/refund/{purchase_id}")
def admin_refund(request: Request, purchase_id: int):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        ok, msg = issue_refund(conn, purchase_id)
        return flash_redirect("/admin", "ok" if ok else "err", msg)
    finally:
        conn.close()


# ---- seller dashboard ---------------------------------------------------------

@app.get("/seller", response_class=HTMLResponse)
def seller_dashboard(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        listings = [dict(r) for r in conn.execute(
            "SELECT * FROM listings WHERE seller_id = ? ORDER BY id DESC",
            (user["id"],))]
        sales = conn.execute(
            """SELECT demo, COUNT(*) AS n,
                      COALESCE(SUM(amount_cents), 0) AS total
               FROM purchases p JOIN listings l ON l.id = p.listing_id
               WHERE l.seller_id = ? AND p.refunded = 0 GROUP BY demo""",
            (user["id"],)).fetchall()
        demo_n = demo_total = paypal_n = paypal_total = 0
        for s in sales:
            if s["demo"]:
                demo_n, demo_total = s["n"], s["total"]
            else:
                paypal_n, paypal_total = s["n"], s["total"]
        earnings = conn.execute(
            """SELECT COALESCE(SUM(seller_cents), 0) AS earnings,
                      COALESCE(SUM(platform_fee_cents), 0) AS fees
               FROM payouts WHERE seller_id = ? AND status = 'paid'""",
            (user["id"],)).fetchone()
        recent_sales = [dict(r) for r in conn.execute(
            """SELECT p.*, l.slug, l.title, u.username AS buyer
               FROM purchases p JOIN listings l ON l.id = p.listing_id
               JOIN users u ON u.id = p.user_id
               WHERE l.seller_id = ? ORDER BY p.id DESC LIMIT 20""",
            (user["id"],))]
        downloads = conn.execute(
            "SELECT COALESCE(SUM(downloads), 0) AS n FROM listings"
            " WHERE seller_id = ?",
            (user["id"],)).fetchone()["n"]
        open_tickets = [dict(r) for r in conn.execute(
            """SELECT t.*, l.title AS listing_title
               FROM tickets t LEFT JOIN listings l ON l.id = t.listing_id
               WHERE t.seller_id = ? AND t.status NOT IN ('resolved', 'closed')
               ORDER BY t.updated_at DESC""",
            (user["id"],))]
        listing_ids = [l["id"] for l in listings]
        recent_reviews = []
        if listing_ids:
            qmarks = ",".join("?" * len(listing_ids))
            recent_reviews = [dict(r) for r in conn.execute(
                f"""SELECT r.*, u.username, l.title, l.slug FROM reviews r
                    JOIN users u ON u.id = r.user_id
                    JOIN listings l ON l.id = r.listing_id
                    WHERE r.listing_id IN ({qmarks})
                    ORDER BY r.id DESC LIMIT 10""",
                listing_ids)]
        return templates.seller_page(
            user, listings, {
                "demo_n": demo_n, "demo_total": demo_total,
                "paypal_n": paypal_n, "paypal_total": paypal_total,
                "earnings": earnings["earnings"],
                "fees": earnings["fees"],
                "downloads": downloads,
            },
            open_tickets, recent_reviews,
            recent_sales=recent_sales,
            paypal_merchant_id=user.get("paypal_merchant_id") or "",
            flash=read_flash(request))
    finally:
        conn.close()


@app.post("/seller/paypal")
def seller_paypal(request: Request, paypal_merchant_id: str = Form("")):
    """Save the seller's PayPal merchant ID for instant payouts.

    Find it in PayPal at Account Settings > Business information >
    PayPal Merchant ID. Without it, paid sales of this seller's
    listings cannot check out. Full automated onboarding (PayPal's
    Partner Referrals API) is a production next step — see README.
    """
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    merchant_id = paypal_merchant_id.strip()
    conn = connect()
    try:
        conn.execute(
            "UPDATE users SET paypal_merchant_id = ? WHERE id = ?",
            (merchant_id, user["id"]))
        conn.commit()
        if merchant_id:
            msg = ("PayPal merchant ID saved — paid sales of your listings "
                   "can now pay out instantly to that PayPal account.")
        else:
            msg = ("PayPal merchant ID removed — paid sales of your listings "
                   "are paused until you connect a PayPal account.")
        return flash_redirect("/seller", "ok", msg)
    finally:
        conn.close()


# ---- forum --------------------------------------------------------------------

@app.get("/forum", response_class=HTMLResponse)
def forum_index(request: Request):
    user = get_user(request)
    conn = connect()
    try:
        cats = [dict(r) for r in conn.execute(
            "SELECT * FROM forum_categories ORDER BY id ASC")]
        for c in cats:
            c["threads"] = conn.execute(
                "SELECT COUNT(*) AS n FROM forum_threads WHERE category_id = ?",
                (c["id"],)).fetchone()["n"]
        recent = [dict(r) for r in conn.execute(
            """SELECT t.*, u.username,
                      (SELECT COUNT(*) FROM forum_replies r
                       WHERE r.thread_id = t.id) AS replies
               FROM forum_threads t JOIN users u ON u.id = t.user_id
               ORDER BY t.updated_at DESC, t.id DESC LIMIT 10""")]
        return templates.forum_index_page(user, cats, recent)
    finally:
        conn.close()


@app.get("/forum/c/{category_id}", response_class=HTMLResponse)
def forum_category(request: Request, category_id: int):
    user = get_user(request)
    conn = connect()
    try:
        cat = conn.execute(
            "SELECT * FROM forum_categories WHERE id = ?",
            (category_id,)).fetchone()
        if not cat:
            return RedirectResponse("/forum", status_code=303)
        threads = [dict(r) for r in conn.execute(
            """SELECT t.*, u.username,
                      (SELECT COUNT(*) FROM forum_replies r
                       WHERE r.thread_id = t.id) AS replies
               FROM forum_threads t JOIN users u ON u.id = t.user_id
               WHERE t.category_id = ? ORDER BY t.updated_at DESC, t.id DESC""",
            (category_id,))]
        return templates.forum_category_page(user, dict(cat), threads,
                                             flash=read_flash(request))
    finally:
        conn.close()


@app.post("/forum/c/{category_id}/new")
def forum_new_thread(request: Request, category_id: int,
                     title: str = Form(...), body: str = Form(...)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        cat = conn.execute(
            "SELECT * FROM forum_categories WHERE id = ?",
            (category_id,)).fetchone()
        if not cat:
            return RedirectResponse("/forum", status_code=303)
        cur = conn.execute(
            """INSERT INTO forum_threads (category_id, user_id, title, body)
               VALUES (?, ?, ?, ?)""",
            (category_id, user["id"], title.strip(), body.strip()))
        record_event(conn, "thread",
                     f"{user['username']} started a forum thread: "
                     f"{title.strip()}")
        conn.commit()
        return RedirectResponse(f"/forum/t/{cur.lastrowid}", status_code=303)
    finally:
        conn.close()


@app.get("/forum/t/{thread_id}", response_class=HTMLResponse)
def forum_thread(request: Request, thread_id: int):
    user = get_user(request)
    conn = connect()
    try:
        row = conn.execute(
            """SELECT t.*, u.username, c.name AS category_name
               FROM forum_threads t
               JOIN users u ON u.id = t.user_id
               JOIN forum_categories c ON c.id = t.category_id
               WHERE t.id = ?""",
            (thread_id,)).fetchone()
        if not row:
            return RedirectResponse("/forum", status_code=303)
        replies = [dict(r) for r in conn.execute(
            """SELECT r.*, u.username FROM forum_replies r
               JOIN users u ON u.id = r.user_id
               WHERE r.thread_id = ? ORDER BY r.id ASC""",
            (thread_id,))]
        return templates.forum_thread_page(user, dict(row), replies,
                                           flash=read_flash(request))
    finally:
        conn.close()


@app.post("/forum/t/{thread_id}/reply")
def forum_reply(request: Request, thread_id: int, body: str = Form(...)):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM forum_threads WHERE id = ?",
                           (thread_id,)).fetchone()
        if not row:
            return RedirectResponse("/forum", status_code=303)
        conn.execute(
            "INSERT INTO forum_replies (thread_id, user_id, body)"
            " VALUES (?, ?, ?)",
            (thread_id, user["id"], body.strip()))
        conn.execute(
            "UPDATE forum_threads SET updated_at = datetime('now')"
            " WHERE id = ?",
            (thread_id,))
        conn.commit()
        return flash_redirect(f"/forum/t/{thread_id}", "ok", "Reply posted.")
    finally:
        conn.close()


# ---- feed -----------------------------------------------------------------------

@app.get("/feed", response_class=HTMLResponse)
def feed(request: Request):
    user = get_user(request)
    conn = connect()
    try:
        events = [dict(r) for r in conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT 50")]
        return templates.feed_page(user, events)
    finally:
        conn.close()


# ---- services -----------------------------------------------------------------------

@app.get("/services", response_class=HTMLResponse)
def services(request: Request):
    return templates.services_page(get_user(request))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
