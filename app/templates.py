"""HTML rendering — server-rendered pages, no JS framework.

The Rusting Dead theme: the game Rust mixed with The Walking Dead comic
book art style — grungy, distressed, blood-red #e11d2e and bone-white on
near-black, heavy condensed comic display type for headings. Body text
stays clean and legible. Brand images (logo + header banner) are served
from /brand/. All user content is escaped with html.escape before it
reaches a template.
"""
import html

from .config import COMMISSION_PCT, DEFAULT_LICENSE_TEXT, GAMES

RED = "#e11d2e"
CATEGORIES = ["Plugins", "Maps", "Tools", "Discord Bots"]

CSS = """
:root{--red:#e11d2e;--bg:#0c0c0e;--panel:#151517;--panel2:#1c1c1f;--line:#2a2a2e;
--text:#f2f2f2;--muted:#9a9aa0;--green:#3fce6d;--amber:#f5a623;
--bone:#efe6d5;--display:Impact,Haettenschweiler,'Arial Narrow Bold','Franklin Gothic Medium','Arial Black',sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background-color:var(--bg);background-image:repeating-linear-gradient(0deg,rgba(255,255,255,.014) 0 1px,transparent 1px 4px);color:var(--text);font-family:system-ui,-apple-system,
Segoe UI,Roboto,sans-serif;line-height:1.5}
a{color:#fff;text-decoration:none}
a:hover{color:var(--red)}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
.topbar{background:#000;border-bottom:2px solid var(--red);padding:10px 0;
position:sticky;top:0;z-index:50}
.topbar .wrap{display:flex;align-items:center;gap:22px;flex-wrap:wrap}
.logo{font-family:var(--display);font-size:26px;font-weight:400;letter-spacing:2px;text-transform:uppercase;display:flex;align-items:center}
.logo b{color:var(--red)}
.logo-text{display:flex;flex-direction:column;line-height:1.02}
.logo-l1{font-size:23px;letter-spacing:2px}
.logo-l2{font-size:12px;letter-spacing:5px;color:var(--red)}
.brand-logo{height:42px;width:42px;border-radius:50%;border:2px solid var(--red);margin-right:10px;object-fit:cover;background:#000;flex:none}
.nav{display:flex;gap:18px;font-weight:600;font-size:14px}
.nav a{color:#ddd}
.searchbar{flex:1;min-width:180px}
.searchbar input{width:100%;background:#1a1a1c;border:1px solid var(--line);
color:#fff;padding:8px 12px;border-radius:4px}
.btn{display:inline-block;background:var(--red);color:#fff;font-weight:800;
padding:10px 18px;border:none;border-radius:2px;cursor:pointer;font-size:14px;
text-transform:uppercase;letter-spacing:.5px;box-shadow:3px 3px 0 rgba(0,0,0,.85)}
.btn:hover{background:#c41526;color:#fff}
.btn.ghost{background:#26262a;border:1px solid var(--line)}
.btn.small{padding:6px 10px;font-size:12px}
.btn:disabled{opacity:.5;cursor:default}
.ticker{background:#111;border-bottom:1px solid var(--line);font-size:13px;
color:var(--muted);padding:6px 0;white-space:nowrap;overflow:hidden}
.ticker b{color:var(--red)}
.hero{background:linear-gradient(rgba(6,6,8,.78),rgba(6,6,8,.88)),url(/brand/therustingdead-header.jpg) center 25%/cover no-repeat #0c0c0e;
border-bottom:2px solid var(--red);padding:64px 0 48px}
.hero h1{font-family:var(--display);font-size:56px;line-height:.95;text-transform:uppercase;font-weight:400;letter-spacing:2px;color:var(--bone);text-shadow:3px 3px 0 #000,6px 6px 0 rgba(225,29,46,.35)}
.hero h1 span{color:var(--red)}
.hero p{color:#cfcfd4;max-width:560px;margin:14px 0 22px}
.hero .row{display:flex;gap:12px;flex-wrap:wrap}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:22px 0}
.stat{background:var(--panel);border:1px solid var(--line);padding:16px}
.stat .n{font-family:var(--display);font-size:32px;font-weight:400;letter-spacing:1px}
.stat .l{font-size:11px;letter-spacing:1.5px;color:var(--muted);text-transform:uppercase}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 0 26px}
.tile{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--red);
padding:16px;font-family:var(--display);font-weight:400;font-size:19px;letter-spacing:1.5px;text-transform:uppercase}
.tile small{display:block;color:var(--muted);font-weight:400;font-size:12px;margin-top:4px}
.section{margin:26px 0}
.section h2{font-family:var(--display);font-size:25px;font-weight:400;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;text-shadow:2px 2px 0 #000}
.section h2 span{color:var(--red)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:2px;overflow:hidden}
.card .banner{height:110px;display:flex;align-items:center;justify-content:center;
font-family:var(--display);font-size:42px;font-weight:400;letter-spacing:2px;color:var(--bone);text-shadow:2px 2px 0 rgba(0,0,0,.8)}
.card .body{padding:12px 14px}
.card .title{font-weight:800;font-size:16px}
.card .meta{color:var(--muted);font-size:12px;margin:6px 0}
.card .price{font-weight:900;color:var(--red);font-size:17px}
.badge{display:inline-block;font-size:11px;font-weight:700;padding:2px 7px;border-radius:3px;
background:#26262a;color:#ddd;text-transform:uppercase}
.badge.wip{background:#5a3a00;color:#ffc857}
.badge.free{background:#0d3b1e;color:var(--green)}
.badge.pending{background:#3a2a00;color:var(--amber)}
.badge.passed{background:#0d3b1e;color:var(--green)}
.badge.failed{background:#3b0d0d;color:#ff6b6b}
.flash{background:#2a1a00;border:1px solid var(--amber);color:#ffd27a;
padding:10px 14px;margin:16px 0;border-radius:4px}
.flash.err{background:#2a0505;border-color:var(--red);color:#ffb3b3}
.flash.ok{background:#0d2b18;border-color:var(--green);color:#b7f0c9}
form.stack{display:flex;flex-direction:column;gap:12px;max-width:640px}
form.stack label{font-weight:700;font-size:13px;text-transform:uppercase;color:var(--muted)}
form.stack input,form.stack textarea,form.stack select{background:#1a1a1c;border:1px solid var(--line);
color:#fff;padding:10px 12px;border-radius:4px;width:100%}
.panel{background:var(--panel);border:1px solid var(--line);padding:20px;margin:16px 0}
table{width:100%;border-collapse:collapse;font-size:14px}
td,th{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--muted);text-transform:uppercase;font-size:11px;letter-spacing:1px}
.tabs{display:flex;gap:2px;border-bottom:1px solid var(--line);margin:18px 0;flex-wrap:wrap}
.tabs a{padding:10px 16px;font-weight:800;font-size:13px;text-transform:uppercase;color:var(--muted)}
.tabs a.active{color:#fff;border-bottom:2px solid var(--red)}
.footer{border-top:1px solid var(--line);margin-top:40px;padding:22px 0;color:var(--muted);font-size:13px}
.muted{color:var(--muted)}
.small{font-size:13px}
.pager{margin:18px 0;display:flex;gap:8px}
.pager a,.pager span{background:var(--panel);border:1px solid var(--line);padding:6px 12px}
.stars{color:#f5a623;letter-spacing:2px}
.kv{display:grid;grid-template-columns:160px 1fr;gap:6px 14px;font-size:14px}
.kv dt{color:var(--muted);text-transform:uppercase;font-size:12px;letter-spacing:1px}
@media(max-width:760px){.stats{grid-template-columns:repeat(2,1fr)}.tiles{grid-template-columns:repeat(2,1fr)}
.hero h1{font-size:36px}.hero{padding:44px 0 34px}}
"""


def esc(s) -> str:
    return html.escape(str(s) if s is not None else "")


def money(cents: int) -> str:
    if cents == 0:
        return "Free"
    return f"${cents / 100:,.2f}"


def money0(cents: int) -> str:
    """Money that always shows $0.00 instead of 'Free' — for totals."""
    return f"${cents / 100:,.2f}"


def banner_color(slug: str) -> str:
    colors = ["#7a1020", "#123a5c", "#14532d", "#4a2c6d", "#5c3a12", "#0f4c4c"]
    return colors[sum(slug.encode()) % len(colors)]


def listing_card(l: dict) -> str:
    wip = ' <span class="badge wip">WIP</span>' if l["is_wip"] else ""
    price = money(l["price_cents"])
    price_html = (
        f'<span class="price">{esc(price)}</span>'
        if l["price_cents"] == 0
        else f'<span class="price">{esc(price)}</span>'
    )
    rating = l.get("rating_avg") or 0
    stars = "★" * round(rating) + "☆" * (5 - round(rating)) if rating else "No ratings yet"
    game = game_name(l.get("game", "rust"))
    return f"""
    <div class="card">
      <a href="/listing/{esc(l['slug'])}">
        <div class="banner" style="background:linear-gradient(135deg,{banner_color(l['slug'])},#151517)">
          {esc(l['title'][:2].upper())}
        </div>
      </a>
      <div class="body">
        <div class="title"><a href="/listing/{esc(l['slug'])}">{esc(l['title'])}</a>{wip}</div>
        <div class="meta">{esc(game)} · {esc(l['category'])} · v{esc(l['version'])} · {esc(l['compatibility'])}</div>
        <div class="meta"><span class="stars">{stars}</span> · {l['downloads']} downloads</div>
        <div>{price_html}</div>
      </div>
    </div>"""


def game_name(slug: str) -> str:
    """Display name for a game slug (Rust now; more games later)."""
    for g_slug, g_name in GAMES:
        if g_slug == slug:
            return g_name
    return slug or "Rust"


def _open_ticket_count(user: dict | None) -> int:
    """Open tickets the user is involved in (buyer, seller, or admin).
    Returns 0 on any error — the badge must never break a page."""
    if not user:
        return 0
    try:
        from .db import connect

        conn = connect()
        try:
            if user.get("is_admin"):
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM tickets"
                    " WHERE status NOT IN ('resolved', 'closed')").fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM tickets"
                    " WHERE status NOT IN ('resolved', 'closed')"
                    " AND (buyer_id = ? OR seller_id = ?)",
                    (user["id"], user["id"])).fetchone()
            return row["n"] if row else 0
        finally:
            conn.close()
    except Exception:
        return 0


def layout(title: str, user: dict | None, body: str, flash: str = "") -> str:
    flash_html = ""
    if flash:
        kind, msg = flash
        flash_html = f'<div class="flash {esc(kind)}">{esc(msg)}</div>'
    if user:
        tickets = _open_ticket_count(user)
        badge = (f' <span class="badge" style="background:var(--red);'
                 f'color:#fff">{tickets}</span>') if tickets else ""
        auth_links = (
            f'<a href="/tickets">Tickets{badge}</a>'
            f'<a href="/sell">Sell</a><a href="/cart">Cart</a>'
            f'<a href="/account">{esc(user["username"])}</a>'
            f'<a href="/logout">Sign out</a>'
            + (' <a href="/admin">Admin</a>' if user.get("is_admin") else '')
        )
    else:
        auth_links = ('<a href="/login">Sign in</a> '
                      '<a href="/signup" class="btn small">Sign up</a>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · The Rusting Dead Mod Marketplace</title>
<link rel="icon" type="image/png" href="/brand/therustingdead-logo-512.png">
<style>{CSS}</style></head>
<body>
<header class="topbar"><div class="wrap">
  <a class="logo" href="/"><img class="brand-logo" src="/brand/therustingdead-logo-512.png" alt="The Rusting Dead logo"><span class="logo-text"><span class="logo-l1">The Rusting Dead</span><span class="logo-l2">Mod Marketplace</span></span></a>
  <nav class="nav"><a href="/browse">Browse</a><a href="/forum">Forum</a>
  <a href="/feed">Feed</a><a href="/services">Services</a>
  <span class="muted" title="Prices are shown in USD.">USD ($)</span></nav>
  <form class="searchbar" action="/browse" method="get">
    <input name="q" placeholder="Search listings, mods, maps, tools..." value="">
  </form>
  <nav class="nav">{auth_links}</nav>
</div></header>
{flash_html}
{body}
<footer class="footer"><div class="wrap">
  <div style="display:flex;gap:12px;align-items:center;margin-bottom:10px">
  <img src="/brand/therustingdead-logo-512.png" alt="The Rusting Dead" style="height:48px;width:48px;border-radius:50%;border:2px solid var(--red);background:#000">
  <div><b style="color:#fff">The Rusting Dead Mod Marketplace</b><br>
  <span class="muted">Hardcore · Quads · Zombies — Rust plugins, maps, tools and Discord bots.</span></div></div>
  A self-hosted marketplace for Rust plugins, maps, tools and Discord bots.
  Listings are reviewed before they go live. Checkout and payouts run on the
  PayPal Commerce Platform — sellers are paid instantly on every sale, the
  platform keeps a {COMMISSION_PCT}% fee. (Stripe was the earlier payment method and is
  set aside, not wired into checkout.) Purchases give you download access from
  your library — there are no licence keys. Sample listings are fictional demo
  data; WeightPlus and AutoWipe_LGSM are Realiztik's real projects.
</div></footer>
</body></html>"""

# ---- page renderers -------------------------------------------------------

def home_page(user, stats, featured, newest, events, settings, flash: str = "") -> str:
    cards = "".join(listing_card(l) for l in featured)
    new_cards = "".join(listing_card(l) for l in newest)
    ticker = " &nbsp;·&nbsp; ".join(esc(e["text"]) for e in events) or "No activity yet."
    discord = settings.get("discord_invite_url") or "#"
    online = settings.get("discord_online", "0")
    members = settings.get("discord_members", "0")
    body = f"""
<div class="ticker"><div class="wrap"><b>● LIVE</b> &nbsp;{ticker}</div></div>
<section class="hero"><div class="wrap">
  <div class="small" style="color:var(--red);letter-spacing:2px;font-weight:800">▸ RUST PLUGINS &amp; MODS</div>
  <h1>The marketplace for<br><span>Rust servers</span></h1>
  <p>Rust plugins, maps, tools, and Discord bots, made and backed by people who run Rust servers.
  Every listing is reviewed before it goes live, with support straight from the creator.</p>
  <div class="row"><a class="btn" href="/browse">Browse mods →</a>
  <a class="btn ghost" href="/sell">Start selling</a></div>
</div></section>
<div class="wrap">
  <div class="stats">
    <div class="stat"><div class="n">{stats['total']}</div><div class="l">Total listings</div></div>
    <div class="stat"><div class="n">{stats['free']}</div><div class="l">Free listings</div></div>
    <div class="stat"><div class="n">{stats['downloads']}</div><div class="l">Downloads</div></div>
    <div class="stat"><div class="n">{stats['users']}</div><div class="l">Users</div></div>
    <div class="stat"><div class="n">⬢ {esc(members)} members</div><div class="l">Discord · {esc(online)} online</div></div>
  </div>
  <div class="tiles">
    <a class="tile" href="/services">Connect your server<small>Full server controls</small></a>
    <a class="tile" href="/browse?category=Discord+Bots">Discord Bots<small>Server helpers</small></a>
  </div>
  <div class="section"><h2><span>▸</span> Featured listings</h2><div class="grid">{cards}</div></div>
  <div class="section"><h2><span>▸</span> Newest listings</h2><div class="grid">{new_cards}</div></div>
  <div class="section"><h2><span>▸</span> Become a creator</h2>
    <div class="panel"><p>Upload your listings, mods, and tools. Set your own prices.
    Earn money doing what you love. Listings go live after a quick review — in minutes, not months.</p>
    <p style="margin-top:10px"><a class="btn" href="/sell">Start selling today</a></p></div></div>
</div>"""
    return layout("The marketplace for Rust servers", user, body, flash)


def browse_page(user, listings, q, category, sort, price_filter, page, pages,
                total, flash: str = "", game: str = "") -> str:
    cards = "".join(listing_card(l) for l in listings) or \
        "<p class='muted'>No listings match that search.</p>"

    def sel(name, value):
        return "selected" if name == value else ""

    opts = "".join(
        f'<option value="{esc(c)}" {sel(c, category)}>{esc(c)}</option>'
        for c in [""] + CATEGORIES
    )
    game_opts = "".join(
        f'<option value="{esc(g[0])}" {sel(g[0], game)}>{esc(g[1])}</option>'
        for g in [("", "All games")] + GAMES
    )
    body = f"""
<div class="wrap"><div class="section"><h2>Browse <span>listings</span></h2>
<p class="muted">{total} listing(s)</p>
<form method="get" action="/browse" style="display:flex;gap:8px;flex-wrap:wrap;margin:14px 0">
  <input name="q" value="{esc(q)}" placeholder="Search..." style="flex:2;min-width:160px;background:#1a1a1c;border:1px solid #2a2a2e;color:#fff;padding:8px 12px;border-radius:4px">
  <select name="game" style="background:#1a1a1c;border:1px solid #2a2a2e;color:#fff;padding:8px">{game_opts}</select>
  <select name="category" style="background:#1a1a1c;border:1px solid #2a2a2e;color:#fff;padding:8px">{opts}</select>
  <select name="sort" style="background:#1a1a1c;border:1px solid #2a2a2e;color:#fff;padding:8px">
    <option value="newest" {sel('newest', sort)}>Newest</option>
    <option value="downloads" {sel('downloads', sort)}>Most downloaded</option>
    <option value="rating" {sel('rating', sort)}>Highest rated</option>
    <option value="price_asc" {sel('price_asc', sort)}>Price: low to high</option>
    <option value="price_desc" {sel('price_desc', sort)}>Price: high to low</option>
  </select>
  <select name="price" style="background:#1a1a1c;border:1px solid #2a2a2e;color:#fff;padding:8px">
    <option value="all" {sel('all', price_filter)}>All prices</option>
    <option value="free" {sel('free', price_filter)}>Free only</option>
    <option value="paid" {sel('paid', price_filter)}>Paid only</option>
  </select>
  <button class="btn small" type="submit">Filter</button>
</form>
<div class="grid">{cards}</div>
<div class="pager">
  {"".join(f'<a href="/browse?q={esc(q)}&game={esc(game)}&category={esc(category)}&sort={esc(sort)}&price={esc(price_filter)}&page={p}">{p}</a>' if p != page else f'<span><b>{p}</b></span>' for p in range(1, pages + 1))}
</div>
</div></div>"""
    return layout("Browse listings", user, body, flash)


def _compile_badge(l: dict) -> str:
    status = l.get("compile_status", "pending")
    date = l.get("compile_date") or ""
    label = {"passed": "✓ Passed", "failed": "✗ Failed",
             "pending": "… Not checked"}.get(status, status)
    when = f" {esc(date)}" if date else ""
    note = ("<p class='small muted'>Compile check is a recorded result, "
            "not a live compile — the seller records it when uploading a "
            "version.</p>")
    return f'<span class="badge {esc(status)}">{esc(label)}{when}</span>{note}'


def listing_page(user, l, seller, versions, reviews, comments, in_cart,
                 in_wishlist, reaction_count, reacted, tab, owned, flash: str = "") -> str:
    wip = ' <span class="badge wip">WIP — unfinished</span>' if l["is_wip"] else ""
    rating = l.get("rating_avg") or 0
    stars = "★" * round(rating) + "☆" * (5 - round(rating)) if rating else "No ratings yet"
    tabs = ["details", "docs", "reviews", "discussion", "versions",
            "support", "license"]
    tab_links = "".join(
        f'<a href="/listing/{esc(l["slug"])}?tab={t}" class="{"active" if t == tab else ""}">{t}</a>'
        for t in tabs
    )
    if tab == "details":
        content = f"<p style='white-space:pre-wrap'>{esc(l['description'])}</p>"
    elif tab == "docs":
        content = f"<p style='white-space:pre-wrap'>{esc(l['docs'] or 'No documentation yet.')}</p>"
    elif tab == "reviews":
        items = "".join(
            f"<div class='panel'><b>{esc(r['username'])}</b> "
            f"<span class='stars'>{'★' * r['rating']}{'☆' * (5 - r['rating'])}</span>"
            f"<p style='white-space:pre-wrap'>{esc(r['body'])}</p>"
            f"<div class='small muted'>{esc(r['created_at'])}</div></div>"
            for r in reviews
        ) or "<p class='muted'>No reviews yet — be the first.</p>"
        form = ""
        if user:
            form = f"""
            <form class="stack" method="post" action="/listing/{esc(l['slug'])}/review">
              <label>Your rating</label>
              <select name="rating"><option>5</option><option>4</option><option>3</option>
              <option>2</option><option>1</option></select>
              <label>Review</label><textarea name="body" rows="3" required></textarea>
              <div><button class="btn" type="submit">Post review</button></div>
            </form>"""
        else:
            form = "<p class='muted'><a href='/login'>Sign in</a> to write a review.</p>"
        content = items + form
    elif tab == "discussion":
        items = "".join(
            f"<div class='panel'><b>{esc(c['username'])}</b>"
            f"<p style='white-space:pre-wrap'>{esc(c['body'])}</p>"
            f"<div class='small muted'>{esc(c['created_at'])}</div></div>"
            for c in comments
        ) or "<p class='muted'>No discussion yet.</p>"
        form = ""
        if user:
            form = f"""
            <form class="stack" method="post" action="/listing/{esc(l['slug'])}/comment">
              <label>Comment</label><textarea name="body" rows="3" required></textarea>
              <div><button class="btn" type="submit">Post comment</button></div>
            </form>"""
        else:
            form = "<p class='muted'><a href='/login'>Sign in</a> to join the discussion.</p>"
        content = items + form
    elif tab == "versions":
        rows = ""
        for v in versions:
            if v["file_path"]:
                dl = (f'<a class="btn small" href="/download/version/'
                      f'{v["id"]}">Download</a>')
            else:
                dl = '<span class="muted">No file</span>'
            rows += (
                f"<tr><td><b>v{esc(v['version'])}</b></td>"
                f"<td>{esc(v['changelog'])}</td>"
                f"<td>{_compile_badge(v)}</td><td>{esc(v['created_at'])}</td>"
                f"<td>{dl}</td></tr>"
            )
        if not rows:
            rows = ("<tr><td colspan='5' class='muted'>No versions recorded "
                    "yet.</td></tr>")
        content = f"<table><tr><th>Version</th><th>Changelog</th><th>Compile check</th><th>Date</th><th>File</th></tr>{rows}</table>"
        if user and user["id"] == l["seller_id"]:
            content += f"""
            <div class="panel"><h3>Upload a new version</h3>
            <form class="stack" method="post" action="/listing/{esc(l['slug'])}/version"
                  enctype="multipart/form-data">
              <label>Version</label><input name="version" required placeholder="e.g. 1.1.0">
              <label>Changelog</label><textarea name="changelog" rows="2" required></textarea>
              <label>Compile check result (recorded, not a live compile)</label>
              <select name="compile_status"><option value="passed">Passed</option>
              <option value="failed">Failed</option><option value="pending">Not checked</option></select>
              <label>Plugin file (.cs, .zip, .json, .md, .txt — max 20 MB)</label>
              <input type="file" name="file">
              <div><button class="btn" type="submit">Upload version</button></div>
            </form></div>"""
    elif tab == "support":
        content = f"<p style='white-space:pre-wrap'>{esc(l['support_text'] or 'Contact the seller via the discussion tab.')}</p>"
        if user:
            content += (
                f"<p style='margin-top:14px'><a class='btn small' "
                f"href='/tickets/new?listing={esc(l['slug'])}'>Open a support ticket</a> "
                f"<a class='btn small ghost' href='/listing/{esc(l['slug'])}/report'>Report this listing</a></p>")
        else:
            content += ("<p class='muted' style='margin-top:14px'>"
                        "<a href='/login'>Sign in</a> to open a support ticket.</p>")
    else:
        content = f"<p style='white-space:pre-wrap'>{esc(l['license_text'] or DEFAULT_LICENSE_TEXT)}</p>"

    buy = ""
    if owned:
        buy = ('<a class="btn" href="/download/'
               f'{esc(l["slug"])}">Download</a>'
               ' <span class="badge passed">Owned</span>')
    elif l["price_cents"] == 0:
        buy = (f'<a class="btn" href="/download/{esc(l["slug"])}">Download free</a>')
    else:
        buy = (f'<form method="post" action="/cart/add/{l["id"]}" style="display:inline">'
               f'<button class="btn" type="submit">Buy now — {esc(money(l["price_cents"]))}</button></form> '
               f'<form method="post" action="/cart/add/{l["id"]}" style="display:inline">'
               f'<button class="btn ghost" type="submit">Add to cart</button></form>')
    wish = ""
    if user:
        wish = (f'<form method="post" action="/listing/{esc(l["slug"])}/wishlist" style="display:inline">'
                f'<button class="btn ghost" type="submit">{"♥ In wishlist" if in_wishlist else "♡ Add to wishlist"}</button></form> '
                f'<form method="post" action="/listing/{esc(l["slug"])}/react" style="display:inline">'
                f'<button class="btn ghost" type="submit">🔥 React ({reaction_count})</button></form>')
    body = f"""
<div class="banner" style="height:220px;display:flex;align-items:center;justify-content:center;
 background:linear-gradient(135deg,{banner_color(l['slug'])},#151517)">
  <span style="font-size:64px;font-weight:900">{esc(l['title'])}</span>
</div>
<div class="wrap">
  <div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:20px">
    <div style="flex:2;min-width:300px">
      <h1 style="font-size:32px;text-transform:uppercase">{esc(l['title'])}{wip}</h1>
      <p class="muted">by <b><a href="/author/{esc(seller['username'])}">{esc(seller['username'])}</a></b> · {esc(game_name(l.get('game', 'rust')))} · {esc(l['category'])} ·
      v{esc(l['version'])} · {esc(l['compatibility'])}</p>
      <p style="margin-top:8px"><span class="stars">{stars}</span>
      {f"{rating:.1f} / 5" if rating else ""}</p>
      <div class="tabs">{tab_links}</div>
      {content}
    </div>
    <div style="flex:1;min-width:260px">
      <div class="panel">
        <div style="font-size:32px;font-weight:900;color:var(--red)">{esc(money(l['price_cents']))}</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0">{buy}</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">{wish}</div>
      </div>
      <div class="panel"><dl class="kv">
        <dt>Views</dt><dd>{l['views']}</dd>
        <dt>Downloads</dt><dd>{l['downloads']}</dd>
        <dt>Purchases</dt><dd>{l['purchases_count']}</dd>
        <dt>Rating</dt><dd>{f"{rating:.1f} / 5" if rating else "—"}</dd>
        <dt>Version</dt><dd>{esc(l['version'])}</dd>
        <dt>Compile check</dt><dd>{_compile_badge(l)}</dd>
        <dt>Game</dt><dd>{esc(game_name(l.get('game', 'rust')))}</dd>
        <dt>Category</dt><dd>{esc(l['category'])}</dd>
        <dt>Compatible</dt><dd>{esc(l['compatibility'])}</dd>
        <dt>Published</dt><dd>{esc(l['created_at'][:10])}</dd>
      </dl></div>
    </div>
  </div>
</div>"""
    return layout(l["title"], user, body, flash)


def auth_page(user, mode: str, error: str = "", notice: str = "") -> str:
    title = "Sign up" if mode == "signup" else "Sign in"
    action = "/signup" if mode == "signup" else "/login"
    extra = ""
    if mode == "signup":
        extra = ('<label>Email</label><input name="email" type="email" required>'
                 '<p class="small muted">The first account created on a fresh '
                 'install becomes the admin. If you sign up as “Realiztik”, '
                 'you claim the sample account that owns WeightPlus and '
                 'AutoWipe_LGSM.</p>')
    err = f'<div class="flash err">{esc(error)}</div>' if error else ""
    note = f'<div class="flash ok">{esc(notice)}</div>' if notice else ""
    forgot = ""
    if mode == "login":
        forgot = ('<p class="muted" style="margin-top:12px">'
                  '<a href="/forgot-password">Forgot your password?</a></p>')
    body = f"""
<div class="wrap"><div class="section"><h2>{title}</h2>{err}{note}
<form class="stack" method="post" action="{action}">
  <label>Username</label><input name="username" required minlength="3">
  {extra}
  <label>Password</label><input name="password" type="password" required minlength="8">
  <div><button class="btn" type="submit">{title}</button></div>
</form>
{forgot}
<p class="muted" style="margin-top:12px">
  {"Already have an account? <a href='/login'>Sign in</a>" if mode == "signup"
   else "No account yet? <a href='/signup'>Sign up</a>"}
</p></div></div>"""
    return layout(title, user, body)


def sell_page(user, error: str = "") -> str:
    err = f'<div class="flash err">{esc(error)}</div>' if error else ""
    opts = "".join(f'<option>{esc(c)}</option>' for c in CATEGORIES)
    game_opts = "".join(
        f'<option value="{esc(g[0])}">{esc(g[1])}</option>' for g in GAMES
    )
    body = f"""
<div class="wrap"><div class="section"><h2>Publish a <span>listing</span></h2>
<p class="muted">Your listing goes into the review queue first — it is not live
until an admin approves it. Every listing is reviewed before it goes live.</p>
{err}
<form class="stack" method="post" action="/sell" enctype="multipart/form-data">
  <label>Title</label><input name="title" required>
  <label>Description</label><textarea name="description" rows="5" required></textarea>
  <label>Game</label><select name="game">{game_opts}</select>
  <label>Category</label><select name="category">{opts}</select>
  <label>Price in USD (0 = free)</label><input name="price" type="number" min="0" step="0.01" value="0" required>
  <label>Version</label><input name="version" value="1.0.0" required>
  <label>Compatibility</label><select name="compatibility">
    <option>Oxide</option><option>Carbon</option><option>Oxide · Carbon</option>
    <option>LinuxGSM</option><option>Other</option></select>
  <label>Documentation</label><textarea name="docs" rows="4"></textarea>
  <label>Licence text</label><textarea name="license_text" rows="2"></textarea>
  <label>Support text</label><textarea name="support_text" rows="2"></textarea>
  <label><input type="checkbox" name="is_wip" value="1"> Mark as work in progress (WIP)</label>
  <label>Plugin file (.cs, .zip, .json, .md, .txt — max 20 MB)</label>
  <input type="file" name="file">
  <div><button class="btn" type="submit">Submit for review</button></div>
</form></div></div>"""
    return layout("Sell a listing", user, body)


def cart_page(user, items, total_cents, paypal_on: bool = False, flash: str = "") -> str:
    rows = "".join(
        f"<tr><td><a href='/listing/{esc(i['slug'])}'>{esc(i['title'])}</a></td>"
        f"<td>{esc(money(i['price_cents']))}</td>"
        f"<td><form method='post' action='/cart/remove/{i['id']}'><button class='btn small ghost' type='submit'>Remove</button></form></td></tr>"
        for i in items
    ) or "<tr><td colspan='3' class='muted'>Your cart is empty.</td></tr>"
    checkout = ""
    if items:
        if paypal_on:
            note = ("<p class='muted'>Secure checkout with PayPal. "
                    "You will be taken to PayPal to pay, then back here. "
                    "Sellers are paid instantly on every sale.</p>")
        else:
            note = ("<p class='muted'>Paid checkout is not configured yet — "
                    "the site owner needs to set PayPal keys in .env. "
                    "Free items still complete; paid items stay in your cart.</p>")
        checkout = f"""
        {note}
        <form method="post" action="/checkout">
          <button class="btn" type="submit">Check out</button>
        </form>"""
    body = f"""
<div class="wrap"><div class="section"><h2>Your <span>cart</span></h2>
<table><tr><th>Listing</th><th>Price</th><th></th></tr>{rows}</table>
<p style="margin:12px 0"><b>Total: {esc(money(total_cents))}</b></p>
{checkout}</div></div>"""
    return layout("Cart", user, body, flash)


def account_page(user, mine, purchases, wishlist_items, flash: str = "") -> str:
    my_rows = "".join(
        f"<tr><td><a href='/listing/{esc(m['slug'])}'>{esc(m['title'])}</a></td>"
        f"<td>{esc(game_name(m.get('game', 'rust')))}</td>"
        f"<td>{esc(m['status'])}</td><td>{esc(money(m['price_cents']))}</td>"
        f"<td>{m['downloads']}</td></tr>" for m in mine
    ) or "<tr><td colspan='5' class='muted'>You have no listings yet. <a href='/sell'>Publish one</a>.</td></tr>"
    p_rows = ""
    for p in purchases:
        if p['refunded']:
            status = ('<span class="badge failed">Refunded — access '
                      'revoked</span>')
            dl = ''
        else:
            status = '<span class="badge passed">Active</span>'
            dl = (f'<a class="btn small" href="/download/{esc(p["slug"])}">'
                  'Download</a>')
        p_rows += (
            f"<tr><td><a href='/listing/{esc(p['slug'])}'>{esc(p['title'])}</a></td>"
            f"<td>{esc(money(p['amount_cents']))}</td>"
            f"<td>{'demo' if p['demo'] else 'paid'}</td>"
            f"<td>{status}</td>"
            f"<td>{dl}</td></tr>"
        )
    if not p_rows:
        p_rows = "<tr><td colspan='5' class='muted'>No purchases yet.</td></tr>"
    w_rows = "".join(
        f"<tr><td><a href='/listing/{esc(w['slug'])}'>{esc(w['title'])}</a></td>"
        f"<td>{esc(money(w['price_cents']))}</td></tr>" for w in wishlist_items
    ) or "<tr><td colspan='2' class='muted'>Wishlist is empty.</td></tr>"
    body = f"""
<div class="wrap"><div class="section"><h2>Account — {esc(user['username'])}</h2>
<p class="muted">{esc(user['email'])} · joined {esc(user['created_at'][:10])}
{' · <span class="badge passed">Admin</span>' if user['is_admin'] else ''}</p>
<p><a class="btn small" href="/seller">Seller dashboard</a>
<a class="btn small ghost" href="/tickets">My support tickets</a></p>
<h3 style="margin-top:20px">My listings</h3>
<table><tr><th>Title</th><th>Game</th><th>Status</th><th>Price</th><th>Downloads</th></tr>{my_rows}</table>
<h3 style="margin-top:20px">My purchases</h3>
<p class="muted small">Purchases give you download access from your library. If a purchase is refunded, download access is revoked.</p>
<table><tr><th>Listing</th><th>Paid</th><th>Type</th><th>Status</th><th></th></tr>{p_rows}</table>
<h3 style="margin-top:20px">Wishlist</h3>
<table><tr><th>Listing</th><th>Price</th></tr>{w_rows}</table>
</div></div>"""
    return layout("Account", user, body, flash)


def admin_page(user, queue, users, sales, settings, reports=None,
               totals=None) -> str:
    reports = reports or []
    totals = totals or {"fees": 0, "sellers": 0, "gross": 0}
    q_rows = ""
    for q in queue:
        status_badge = (
            '<span class="badge pending">Flagged — needs human review</span>'
            if q['status'] == 'flagged'
            else '<span class="badge pending">Pending</span>')
        note = esc(q.get('review_note') or '—')
        q_rows += (
            f"<tr><td><a href='/listing/{esc(q['slug'])}'>{esc(q['title'])}</a></td>"
            f"<td>{esc(q['seller'])}</td>"
            f"<td>{esc(game_name(q.get('game', 'rust')))}</td>"
            f"<td>{esc(q['category'])}</td>"
            f"<td>{esc(money(q['price_cents']))}</td>"
            f"<td>{status_badge}</td>"
            f"<td style='white-space:pre-wrap'>{note}</td>"
            f"<td><form method='post' action='/admin/approve/{q['id']}' style='display:inline'>"
            f"<button class='btn small' type='submit'>Approve</button></form>"
            f"<form method='post' action='/admin/flag/{q['id']}' style='margin-top:6px'>"
            f"<input name='reason' placeholder='Reason to flag' style='background:#1a1a1c;border:1px solid #2a2a2e;color:#fff;padding:6px 8px;border-radius:4px;width:180px'> "
            f"<button class='btn small ghost' type='submit'>Flag for review</button></form>"
            f"<form method='post' action='/admin/reject/{q['id']}' style='margin-top:6px'>"
            f"<input name='reason' placeholder='Reason for rejection' style='background:#1a1a1c;border:1px solid #2a2a2e;color:#fff;padding:6px 8px;border-radius:4px;width:180px'> "
            f"<button class='btn small ghost' type='submit'>Reject</button></form></td></tr>"
        )
    if not q_rows:
        q_rows = ("<tr><td colspan='8' class='muted'>Review queue is "
                  "empty.</td></tr>")
    r_rows = "".join(
        f"<tr><td>{esc(r['reporter'])}</td>"
        f"<td>{esc(r['listing_title'] or '—')}</td>"
        f"<td>{esc(r['reported_user'] or '—')}</td>"
        f"<td>{esc(r['reason'])}</td>"
        f"<td style='white-space:pre-wrap'>{esc(r['body'])}</td>"
        f"<td><form method='post' action='/admin/reports/{r['id']}/dismiss' style='display:inline'>"
        f"<button class='btn small ghost' type='submit'>Dismiss</button></form> "
        + (f"<form method='post' action='/admin/reports/{r['id']}/hide' style='display:inline'>"
           f"<button class='btn small' type='submit'>Hide listing</button></form>"
           if r.get('listing_id') else "")
        + "</td></tr>"
        for r in reports
    ) or "<tr><td colspan='6' class='muted'>No open reports.</td></tr>"
    u_rows = "".join(
        f"<tr><td>{esc(u['username'])}</td><td>{esc(u['email'])}</td>"
        f"<td>{'admin' if u['is_admin'] else 'user'}{' · sample' if u['is_sample'] else ''}</td>"
        f"<td>{esc(u['created_at'][:10])}</td></tr>" for u in users
    )
    s_rows = ""
    for s in sales:
        if s['refunded']:
            status = '<span class="badge failed">Refunded</span>'
            refund_btn = ''
        elif s['demo'] or s['amount_cents'] == 0:
            status = '<span class="badge">Free / demo</span>'
            refund_btn = ''
        else:
            status = '<span class="badge passed">Paid</span>'
            refund_btn = (
                f"<form method='post' action='/admin/refund/{s['id']}' "
                f"style='display:inline'><button class='btn small ghost' "
                f"type='submit'>Refund</button></form>")
        s_rows += (
            f"<tr><td><a href='/listing/{esc(s['slug'])}'>{esc(s['title'])}</a></td>"
            f"<td>{esc(s['buyer'])}</td><td>{esc(money(s['amount_cents']))}</td>"
            f"<td>{esc(money(s.get('platform_fee_cents') or 0))}</td>"
            f"<td>{esc(money(s.get('seller_amount_cents') or 0))}</td>"
            f"<td>{status}</td><td>{esc(s['created_at'])}</td><td>{refund_btn}</td></tr>"
        )
    if not s_rows:
        s_rows = "<tr><td colspan='8' class='muted'>No sales yet.</td></tr>"
    body = f"""
<div class="wrap"><div class="section"><h2>Admin <span>dashboard</span></h2>
<div class="panel"><h3>How review works</h3>
<p class="small">Every listing is reviewed for security vulnerabilities, malicious code,
code quality, performance issues, and listing completeness before it goes live. Outcomes:</p>
<ul class="small" style="margin:8px 0 0 18px">
<li><b>Approve</b> — goes live immediately.</li>
<li><b>Flag for review</b> — held for a closer human review, typically 24–48 hours. The seller is emailed the reason.</li>
<li><b>Reject</b> — not published. Give a specific reason — the seller is emailed it and can fix and re-submit.</li>
</ul></div>
<h3>Review queue — listings waiting for approval</h3>
<table><tr><th>Title</th><th>Seller</th><th>Game</th><th>Category</th><th>Price</th><th>Status</th><th>Review note</th><th>Actions</th></tr>{q_rows}</table>
<h3 style="margin-top:20px">Reports — open</h3>
<table><tr><th>Reporter</th><th>Listing</th><th>Reported user</th><th>Reason</th><th>Details</th><th>Actions</th></tr>{r_rows}</table>
<h3 style="margin-top:20px">Users</h3>
<table><tr><th>Username</th><th>Email</th><th>Role</th><th>Joined</th></tr>{u_rows}</table>
<h3 style="margin-top:20px">Sales — PayPal Commerce, {COMMISSION_PCT}% platform fee</h3>
<p class="muted small">Paid sales (not refunded): gross {esc(money0(totals['gross']))} · platform fees {esc(money0(totals['fees']))} · paid to sellers {esc(money0(totals['sellers']))}. Sellers are paid instantly on every sale by PayPal. Chargebacks are absorbed by the platform — that is a business policy, no code handles them. A refund revokes the buyer's download access.</p>
<table><tr><th>Listing</th><th>Buyer</th><th>Amount</th><th>Platform fee</th><th>Seller share</th><th>Status</th><th>Date</th><th></th></tr>{s_rows}</table>
<h3 style="margin-top:20px">Community settings</h3>
<form class="stack" method="post" action="/admin/settings">
  <label>Discord invite URL</label>
  <input name="discord_invite_url" value="{esc(settings.get('discord_invite_url', ''))}">
  <label>Discord members online</label>
  <input name="discord_online" value="{esc(settings.get('discord_online', '0'))}">
  <label>Discord members total</label>
  <input name="discord_members" value="{esc(settings.get('discord_members', '0'))}">
  <div><button class="btn" type="submit">Save settings</button></div>
</form></div></div>"""
    return layout("Admin", user, body)


# ---- v2 pages ---------------------------------------------------------------

def checkout_success_page(user, purchases) -> str:
    if purchases:
        rows = "".join(
            f"<tr><td><a href='/listing/{esc(p['slug'])}'>{esc(p['title'])}</a></td>"
            f"<td>{esc(money(p['amount_cents']))}</td>"
            f"<td><a class='btn small' href='/download/{esc(p['slug'])}'>Download</a></td></tr>"
            for p in purchases
        )
        body = f"""
<div class="wrap"><div class="section"><h2>Payment <span>complete</span></h2>
<p>Thank you — your payment went through and your purchases are ready.</p>
<table><tr><th>Listing</th><th>Paid</th><th></th></tr>{rows}</table>
<p class="muted" style="margin-top:12px">Your purchases are in your library —
download any time from <a href="/account">Account → My purchases</a>.</p>
</div></div>"""
    else:
        body = """
<div class="wrap"><div class="section"><h2>Payment <span>complete</span></h2>
<p class="muted">No new purchases were recorded for this payment — you may
already own these listings. Check <a href="/account">My purchases</a>.</p>
</div></div>"""
    return layout("Payment complete", user, body)


def forgot_page(user, sent: bool = False, dev_link: str | None = None) -> str:
    if sent:
        dev = ""
        if dev_link:
            dev = (f'<div class="panel"><b>DEV MODE — email is not '
                   f'configured.</b><p class="small">SMTP is not set up, so '
                   f'the reset link is shown here, only to you, instead of '
                   f'being emailed. Do not share it. It expires in 1 hour.'
                   f'</p><p><a href="{esc(dev_link)}">{esc(dev_link)}</a>'
                   f'</p></div>')
        body = f"""
<div class="wrap"><div class="section"><h2>Reset <span>password</span></h2>
<p>If an account exists for that email or username, a password reset link
has been sent (or is shown below in dev mode).</p>{dev}
<p><a href="/login">Back to sign in</a></p></div></div>"""
        return layout("Reset password", user, body)
    body = """
<div class="wrap"><div class="section"><h2>Reset <span>password</span></h2>
<p class="muted">Enter your email or username and we will send you a reset
link (valid 1 hour).</p>
<form class="stack" method="post" action="/forgot-password">
  <label>Email or username</label><input name="identifier" required>
  <div><button class="btn" type="submit">Send reset link</button></div>
</form></div></div>"""
    return layout("Reset password", user, body)


def reset_page(user, token: str, error: str = "") -> str:
    err = f'<div class="flash err">{esc(error)}</div>' if error else ""
    body = f"""
<div class="wrap"><div class="section"><h2>Set a <span>new password</span></h2>{err}
<form class="stack" method="post" action="/reset-password">
  <input type="hidden" name="token" value="{esc(token)}">
  <label>New password (8+ characters)</label>
  <input name="password" type="password" required minlength="8">
  <div><button class="btn" type="submit">Reset password</button></div>
</form></div></div>"""
    return layout("Set a new password", user, body)


def tickets_page(user, tickets, flash: str = "") -> str:
    rows = "".join(
        f"<tr><td><a href='/tickets/{t['id']}'>#{t['id']} — {esc(t['subject'])}</a></td>"
        f"<td>{esc(t['listing_title'] or 'General')}</td>"
        f"<td>{esc(t['buyer'])}</td><td>{esc(t['seller'] or '—')}</td>"
        f"<td><span class='badge'>{esc(t['status'])}</span></td>"
        f"<td>{esc(t['updated_at'][:16])}</td></tr>"
        for t in tickets
    ) or "<tr><td colspan='6' class='muted'>No tickets yet.</td></tr>"
    body = f"""
<div class="wrap"><div class="section"><h2>Support <span>tickets</span></h2>
<p><a class="btn small" href="/tickets/new">Open a ticket</a></p>
<table><tr><th>Ticket</th><th>Listing</th><th>Buyer</th><th>Seller</th>
<th>Status</th><th>Updated</th></tr>{rows}</table>
<p class="muted small" style="margin-top:10px">Statuses: open → awaiting-seller
→ awaiting-buyer → resolved → closed. Replying reopens a resolved ticket.</p>
</div></div>"""
    return layout("Support tickets", user, body, flash)


def new_ticket_page(user, listing: dict | None) -> str:
    if listing:
        head = (f"<p>About listing: <b>{esc(listing['title'])}</b> — the "
                f"seller will be notified.</p>"
                f"<input type='hidden' name='listing_id' value='{listing['id']}'>")
    else:
        head = ("<p class='muted'>General ticket — not about a specific "
                "listing. An admin will pick it up.</p>"
                "<input type='hidden' name='listing_id' value='0'>")
    body = f"""
<div class="wrap"><div class="section"><h2>Open a <span>ticket</span></h2>{head}
<form class="stack" method="post" action="/tickets/new">
  <label>Subject</label><input name="subject" required maxlength="120">
  <label>What happened?</label><textarea name="body" rows="6" required></textarea>
  <div><button class="btn" type="submit">Open ticket</button></div>
</form></div></div>"""
    return layout("Open a ticket", user, body)


def ticket_detail_page(user, ticket, replies, flash: str = "") -> str:
    items = "".join(
        f"<div class='panel'><b>{esc(r['username'])}</b> "
        f"<span class='small muted'>{esc(r['created_at'])}</span>"
        f"<p style='white-space:pre-wrap'>{esc(r['body'])}</p></div>"
        for r in replies
    ) or "<p class='muted'>No replies yet.</p>"
    status_opts = "".join(
        f"<option value='{s}' {'selected' if s == ticket['status'] else ''}>{s}</option>"
        for s in ("open", "awaiting-seller", "awaiting-buyer", "resolved",
                  "closed")
    )
    listing_line = ""
    if ticket.get("listing_title"):
        listing_line = (f"<p class='muted'>Listing: <a href='/listing/"
                        f"{esc(ticket['listing_slug'])}'>"
                        f"{esc(ticket['listing_title'])}</a></p>")
    body = f"""
<div class="wrap"><div class="section">
<h2>Ticket #{ticket['id']} — {esc(ticket['subject'])}</h2>
<p><span class='badge'>{esc(ticket['status'])}</span> &nbsp;
Buyer: <b>{esc(ticket['buyer'])}</b> &nbsp;
Seller: <b>{esc(ticket['seller'] or '—')}</b></p>
{listing_line}
<div style="margin:18px 0">{items}</div>
<form class="stack" method="post" action="/tickets/{ticket['id']}/reply">
  <label>Reply</label><textarea name="body" rows="4" required></textarea>
  <div><button class="btn" type="submit">Post reply</button></div>
</form>
<form class="stack" method="post" action="/tickets/{ticket['id']}/status" style="margin-top:16px">
  <label>Change status</label>
  <select name="status">{status_opts}</select>
  <div><button class="btn ghost" type="submit">Update status</button></div>
</form>
</div></div>"""
    return layout(f"Ticket #{ticket['id']}", user, body, flash)


def report_page(user, listing) -> str:
    opts = "".join(
        f"<option>{esc(r)}</option>" for r in
        ("Spam", "Scam / fraud", "Stolen content", "Malware",
         "Offensive content", "Other")
    )
    body = f"""
<div class="wrap"><div class="section"><h2>Report</h2>
<p class="muted">Reporting: <b>{esc(listing['title'])}</b> by
<b>{esc(listing['seller_id'])}</b>. An admin will review it.</p>
<form class="stack" method="post" action="/listing/{esc(listing['slug'])}/report">
  <label>What are you reporting?</label>
  <select name="target">
    <option value="listing">This listing</option>
    <option value="seller">The seller</option>
  </select>
  <label>Reason</label><select name="reason">{opts}</select>
  <label>Details</label><textarea name="body" rows="4"></textarea>
  <div><button class="btn" type="submit">Send report</button></div>
</form></div></div>"""
    return layout("Report", user, body)


def seller_page(user, listings, stats, open_tickets, recent_reviews,
                flash: str = "", recent_sales=None, paypal_merchant_id: str = "") -> str:
    l_rows = "".join(
        f"<tr><td><a href='/listing/{esc(l['slug'])}'>{esc(l['title'])}</a></td>"
        f"<td><span class='badge'>{esc(l['status'])}</span></td>"
        f"<td>{esc(money(l['price_cents']))}</td>"
        f"<td>{l['downloads']}</td><td>{l['purchases_count']}</td>"
        f"<td>{f'{l['rating_avg']:.1f}' if l['rating_avg'] else '—'}</td></tr>"
        for l in listings
    ) or "<tr><td colspan='6' class='muted'>No listings yet. <a href='/sell'>Publish one</a>.</td></tr>"
    t_rows = "".join(
        f"<tr><td><a href='/tickets/{t['id']}'>#{t['id']} — {esc(t['subject'])}</a></td>"
        f"<td>{esc(t['listing_title'] or 'General')}</td>"
        f"<td><span class='badge'>{esc(t['status'])}</span></td></tr>"
        for t in open_tickets
    ) or "<tr><td colspan='3' class='muted'>No open tickets on your listings.</td></tr>"
    r_rows = "".join(
        f"<tr><td><a href='/listing/{esc(r['slug'])}'>{esc(r['title'])}</a></td>"
        f"<td>{esc(r['username'])}</td>"
        f"<td><span class='stars'>{'★' * r['rating']}{'☆' * (5 - r['rating'])}</span></td>"
        f"<td style='white-space:pre-wrap'>{esc(r['body'])}</td></tr>"
        for r in recent_reviews
    ) or "<tr><td colspan='4' class='muted'>No reviews yet.</td></tr>"
    sale_rows = ""
    for s in (recent_sales or []):
        if s['refunded']:
            status = '<span class="badge failed">Refunded</span>'
            refund_btn = ''
        elif s['demo'] or s['amount_cents'] == 0:
            status = '<span class="badge">Free / demo</span>'
            refund_btn = ''
        else:
            status = '<span class="badge passed">Paid</span>'
            refund_btn = (
                f"<form method='post' action='/seller/refund/{s['id']}' "
                f"style='display:inline'><button class='btn small ghost' "
                f"type='submit'>Refund</button></form>")
        sale_rows += (
            f"<tr><td><a href='/listing/{esc(s['slug'])}'>{esc(s['title'])}</a></td>"
            f"<td>{esc(s['buyer'])}</td><td>{esc(money(s['amount_cents']))}</td>"
            f"<td>{esc(money(s.get('seller_amount_cents') or 0))}</td>"
            f"<td>{status}</td><td>{esc(s['created_at'][:16])}</td><td>{refund_btn}</td></tr>"
        )
    if not sale_rows:
        sale_rows = "<tr><td colspan='7' class='muted'>No sales yet.</td></tr>"
    if paypal_merchant_id:
        paypal_status = (f"Connected: <b>{esc(paypal_merchant_id)}</b> — "
                         f"paid sales pay out instantly to this PayPal account.")
    else:
        paypal_status = ("No PayPal account connected yet — paid sales of your "
                         "listings are paused until you connect one.")
    body = f"""
<div class="wrap"><div class="section"><h2>Seller <span>dashboard</span></h2>
<p class="muted">Signed in as {esc(user['username'])}</p>
<div class="stats">
  <div class="stat"><div class="n">{stats['demo_n'] + stats['paypal_n']}</div><div class="l">Sales</div></div>
  <div class="stat"><div class="n">{esc(money0(stats['demo_total'] + stats['paypal_total']))}</div><div class="l">Revenue, gross</div></div>
  <div class="stat"><div class="n">{esc(money0(stats['earnings']))}</div><div class="l">Your earnings (85%)</div></div>
  <div class="stat"><div class="n">{esc(money0(stats['fees']))}</div><div class="l">Platform fees ({COMMISSION_PCT}%)</div></div>
  <div class="stat"><div class="n">{stats['downloads']}</div><div class="l">Downloads</div></div>
</div>
<div class="panel"><h3>PayPal payouts — instant, on every sale</h3>
<p class="small">{paypal_status}</p>
<form class="stack" method="post" action="/seller/paypal">
  <label>PayPal merchant ID</label>
  <input name="paypal_merchant_id" value="{esc(paypal_merchant_id)}" placeholder="e.g. A1B2C3D4E5F6G">
  <p class="small muted">Find it in PayPal: Account Settings → Business information → PayPal Merchant ID.
  Automated onboarding (PayPal Partner Referrals) is a later step — for now the merchant ID is how
  payouts are connected. You keep 85% of every paid sale; the platform keeps {COMMISSION_PCT}%.</p>
  <div><button class="btn" type="submit">Save PayPal merchant ID</button></div>
</form></div>
<h3>My listings</h3>
<table><tr><th>Title</th><th>Status</th><th>Price</th><th>Downloads</th><th>Sales</th><th>Rating</th></tr>{l_rows}</table>
<h3 style="margin-top:20px">Recent sales</h3>
<p class="muted small">Refunding a sale returns the buyer's money and revokes their download access.</p>
<table><tr><th>Listing</th><th>Buyer</th><th>Amount</th><th>Your share</th><th>Status</th><th>Date</th><th></th></tr>{sale_rows}</table>
<h3 style="margin-top:20px">Open tickets on my listings</h3>
<table><tr><th>Ticket</th><th>Listing</th><th>Status</th></tr>{t_rows}</table>
<h3 style="margin-top:20px">Recent reviews</h3>
<table><tr><th>Listing</th><th>Reviewer</th><th>Rating</th><th>Review</th></tr>{r_rows}</table>
</div></div>"""
    return layout("Seller dashboard", user, body, flash)


def forum_index_page(user, categories, recent) -> str:
    c_rows = "".join(
        f"<tr><td><a href='/forum/c/{c['id']}'><b>{esc(c['name'])}</b></a><br>"
        f"<span class='muted small'>{esc(c['description'])}</span></td>"
        f"<td>{c['threads']} threads</td></tr>"
        for c in categories
    )
    t_rows = "".join(
        f"<tr><td><a href='/forum/t/{t['id']}'>{esc(t['title'])}</a></td>"
        f"<td>{esc(t['username'])}</td><td>{t['replies']} replies</td>"
        f"<td>{esc(t['updated_at'][:16])}</td></tr>"
        for t in recent
    ) or "<tr><td colspan='4' class='muted'>No threads yet — start one.</td></tr>"
    body = f"""
<div class="wrap"><div class="section"><h2>Forum</h2>
<table><tr><th>Category</th><th>Threads</th></tr>{c_rows}</table>
<h3 style="margin-top:20px">Recent threads</h3>
<table><tr><th>Thread</th><th>Author</th><th>Replies</th><th>Last active</th></tr>{t_rows}</table>
</div></div>"""
    return layout("Forum", user, body)


def forum_category_page(user, category, threads, flash: str = "") -> str:
    t_rows = "".join(
        f"<tr><td><a href='/forum/t/{t['id']}'>{esc(t['title'])}</a></td>"
        f"<td>{esc(t['username'])}</td><td>{t['replies']} replies</td>"
        f"<td>{esc(t['updated_at'][:16])}</td></tr>"
        for t in threads
    ) or "<tr><td colspan='4' class='muted'>No threads in this category yet.</td></tr>"
    form = ""
    if user:
        form = f"""
        <div class="panel"><h3>Start a thread</h3>
        <form class="stack" method="post" action="/forum/c/{category['id']}/new">
          <label>Title</label><input name="title" required maxlength="120">
          <label>Post</label><textarea name="body" rows="4" required></textarea>
          <div><button class="btn" type="submit">Post thread</button></div>
        </form></div>"""
    else:
        form = "<p class='muted'><a href='/login'>Sign in</a> to start a thread.</p>"
    body = f"""
<div class="wrap"><div class="section"><h2>{esc(category['name'])}</h2>
<p class="muted">{esc(category['description'])}</p>
<p><a href="/forum">← All categories</a></p>
<table><tr><th>Thread</th><th>Author</th><th>Replies</th><th>Last active</th></tr>{t_rows}</table>
{form}</div></div>"""
    return layout(category["name"], user, body, flash)


def forum_thread_page(user, thread, replies, flash: str = "") -> str:
    items = "".join(
        f"<div class='panel'><b>{esc(r['username'])}</b> "
        f"<span class='small muted'>{esc(r['created_at'])}</span>"
        f"<p style='white-space:pre-wrap'>{esc(r['body'])}</p></div>"
        for r in replies
    ) or "<p class='muted'>No replies yet.</p>"
    form = ""
    if user:
        form = f"""
        <form class="stack" method="post" action="/forum/t/{thread['id']}/reply">
          <label>Reply</label><textarea name="body" rows="4" required></textarea>
          <div><button class="btn" type="submit">Post reply</button></div>
        </form>"""
    else:
        form = "<p class='muted'><a href='/login'>Sign in</a> to reply.</p>"
    body = f"""
<div class="wrap"><div class="section">
<p><a href="/forum">← Forum</a> · <a href="/forum/c/{thread['category_id']}">{esc(thread['category_name'])}</a></p>
<h2>{esc(thread['title'])}</h2>
<p class="muted">by <b>{esc(thread['username'])}</b> · {esc(thread['created_at'][:16])}</p>
<div class="panel"><p style="white-space:pre-wrap">{esc(thread['body'])}</p></div>
<div style="margin:18px 0">{items}</div>
{form}</div></div>"""
    return layout(thread["title"], user, body, flash)


def feed_page(user, events) -> str:
    items = "".join(
        f"<div class='panel'><span class='badge'>{esc(e['kind'])}</span> "
        f"{esc(e['text'])}"
        f"<div class='small muted'>{esc(e['created_at'])}</div></div>"
        for e in events
    ) or "<p class='muted'>No activity yet.</p>"
    body = f"""
<div class="wrap"><div class="section"><h2>Feed</h2>
<p class="muted">New listings, updates, purchases and reviews across the marketplace.</p>
{items}</div></div>"""
    return layout("Feed", user, body)


def services_page(user) -> str:
    body = """
<div class="wrap"><div class="section"><h2>Services</h2>
<p class="muted">What The Rusting Dead Mod Marketplace does for sellers and server owners, beyond the listings themselves.</p>
<div class="panel"><h3>Listing review</h3>
<p>Every listing is reviewed by an admin before it goes live — the same
promise as the homepage. Review covers security vulnerabilities, malicious
code, code quality, performance issues, and listing completeness. Outcomes:
approved (goes live), flagged for a closer human review (typically 24–48
hours), or rejected with a specific reason. Rejected listings can be fixed
and re-submitted.</p></div>
<div class="panel"><h3>Compile check</h3>
<p>Sellers record a compile-check result (passed / failed / not checked, with
a date) when they upload a version. It is a recorded result, not a live
compile — the listing page says so, and a failed check warns buyers before
they download.</p></div>
<div class="panel"><h3>Support tickets</h3>
<p>Buyers open a ticket on a listing, or a general ticket from their
account. Sellers and admins reply in-thread, with statuses open,
awaiting-seller, awaiting-buyer, resolved and closed. Open a ticket from
any listing's Support tab.</p></div>
<div class="panel"><h3>Server connect help</h3>
<p>Running a Rust server of your own? The marketplace's own server tooling
— AutoWipe_LGSM for monthly wipes — is listed here. For anything else,
open a ticket and an admin will point you in the right direction.</p></div>
<div class="panel"><h3>Sell your work</h3>
<p>Publish plugins, maps, tools and Discord bots, set your own price, and
get paid instantly on every sale through PayPal — you keep 85%, the
platform keeps a {COMMISSION_PCT}% fee. Connect your PayPal account from the
seller dashboard first. Start from the
<a href="/sell">Sell</a> page.</p></div>
</div></div>"""
    return layout("Services", user, body)


def author_page(user, author, listings) -> str:
    cards = "".join(listing_card(l) for l in listings) or \
        "<p class='muted'>No live listings yet.</p>"
    bio = esc(author.get('bio') or 'No bio yet.')
    body = f"""
<div class="wrap"><div class="section">
  <h2>{esc(author['username'])}</h2>
  <p class="muted">{bio}</p>
  <p class="muted small">Joined {esc(author['created_at'][:10])}
  {' · <span class="badge passed">Admin</span>' if author['is_admin'] else ''}</p>
  <h3 style="margin-top:20px">Listings</h3>
  <div class="grid">{cards}</div>
</div></div>"""
    return layout(f"{author['username']} — author", user, body)
