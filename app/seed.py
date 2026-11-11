"""Seed data — runs once, only when the database has no users yet.

Two listings are REAL projects belonging to Realiztik:
  * WeightPlus — his Rust Oxide plugin (WIP, v2.0.6, unfinished)
  * AutoWipe_LGSM — his monthly-wipe tool for LGSM Rust servers
Everything else is clearly fictional SAMPLE data (sample users, sample
plugins) so the marketplace has something to browse on first run. Sample
users have no usable password (password_hash is empty) and are marked
is_sample=1. Realiztik claims the sample "Realiztik" account by signing
up with that username — the signup flow sets the password and makes it a
real account (and admin, if no admin exists yet).
"""
from .db import connect

SAMPLE_USERS = [
    # username, email, bio
    ("Realiztik", "realiztik@example.local",
     "Rust server owner (The Rusting Dead) and plugin maintainer."),
    ("Razor", "razor@example.local",
     "Server owner, plugin author. Writes raid and PvP tooling."),
    ("Bxcas", "bxcas@example.local",
     "Map and tooling author. Likes wipe timers and Discord bots."),
    ("HA1FAL1VE", "ha1fal1ve@example.local",
     "PvE server admin. Builds gather and event plugins."),
]

# title, slug, category, price_cents, version, compatibility, seller,
# featured, is_wip, compile_status, compile_date, views, downloads,
# purchases, description, docs, license, support
LISTINGS = [
    (
        "WeightPlus", "weightplus", "Plugins", 0, "2.0.6", "Oxide",
        "Realiztik", 1, 1, "pending", None, 412, 96, 0,
        "A plugin that displays the player's carried weight in a HUD with "
        "encumbrance effects. Over 75% of max weight you move slower; at "
        "100% you can't move at all. Permission: weightplus.default. "
        "Default max weight is 100. Chat messages show your current load "
        "in colour so you always know where you stand.\n\n"
        "STATUS: WORK IN PROGRESS — UNFINISHED. Version 2.0.6 is the last "
        "version from the June 2025 build thread. No successful Oxide "
        "compile has been shown yet, and there is no release. Listed here "
        "so the work is visible, not because it is ready to run.",
        "Install: drop WeightPlus.cs into oxide/plugins, grant the "
        "weightplus.default permission, reload. Config: max weight, "
        "slowdown thresholds and HUD colours are in the generated config "
        "file. Requires Oxide on a Rust server.",
        "MIT — free to use, modify and share. No warranty; this is "
        "unfinished work in progress.",
        "Best effort via the discussion tab. This is a side project and "
        "it is currently unfinished — bug reports are welcome, fixes may "
        "take a while.",
    ),
    (
        "AutoWipe_LGSM", "autowipe-lgsm", "Tools", 0, "1.0.0", "LinuxGSM",
        "Realiztik", 1, 0, "passed", "2026-07-03", 388, 74, 0,
        "Monthly map + blueprint wipe tool for LinuxGSM (LGSM) Rust "
        "servers. Cron-driven wipe scheduling with a seed rotation table "
        "(June 2026 – May 2027), idempotent same-day re-wipes, Discord "
        "webhook notifications, and a run_wipe.sh wrapper. Built for The "
        "Rusting Dead | Zombies | Hardcore (monthly wipes, worldsize "
        "4250). Includes a config schema (wipe_config.json) and an "
        "examples folder. mcrcon support is optional.",
        "Install: clone into your LGSM install, edit config/wipe_config."
        "json with your seeds and schedule, add the cron entry "
        "(e.g. */5 * * * * /data1/AutoWipe_LGSM/scripts/run_wipe.sh). "
        "The script does not catch up missed wipes — the cron entry has "
        "to exist. July 2026 was missed for exactly that reason; the "
        "missed wipe was run manually on 2026-07-03 and succeeded.",
        "MIT — free to use and modify. mcrcon (Tiiffi) is under the zlib "
        "licence; keep its notice if you redistribute it.",
        "Issues and questions via the discussion tab. Used in production "
        "on The Rusting Dead; the July 2026 wipe ran successfully.",
    ),
    (
        "RaidAlarm", "raidalarm", "Plugins", 999, "1.4.2", "Oxide · Carbon",
        "Razor", 1, 0, "passed", "2026-11-05", 577, 210, 31,
        "SAMPLE PLUGIN — fictional listing for demo purposes. Sends a "
        "Discord alert the moment a raid starts on your server: who, "
        "where, and with what. Configurable cooldowns, per-team pings, "
        "and a quiet-hours window so your players are not woken at 4am.",
        "Install: drop RaidAlarm.cs into oxide/plugins, set your Discord "
        "webhook URL in the config, reload. Requires a Discord webhook.",
        "Sample licence — this is demo data, not a real product.",
        "Sample support text — this is demo data, not a real product.",
    ),
    (
        "Abandoned Factory", "abandoned-factory", "Maps", 1499, "1.2.0",
        "Oxide · Carbon", "Razor", 1, 0, "passed", "2026-10-28", 1204, 388, 64,
        "SAMPLE MAP — fictional listing for demo purposes. A custom "
        "monument: a derelict factory complex with loot rooms, parkour "
        "routes, NPC scientists and a rooftop heli pad. Built for 3k "
        "procedural maps; includes a prefab pack and a spawn config.",
        "Install: copy the map files into your server's maps folder and "
        "add the monument to your map config. Works with Oxide and "
        "Carbon. Requires a map wipe to take effect.",
        "Sample licence — this is demo data, not a real product.",
        "Sample support text — this is demo data, not a real product.",
    ),
    (
        "WipeCountdown", "wipecountdown", "Tools", 0, "2.1.0", "Oxide",
        "Bxcas", 0, 0, "passed", "2026-11-02", 690, 302, 0,
        "SAMPLE PLUGIN — fictional listing for demo purposes. A clean "
        "wipe countdown HUD for your players: days, hours and minutes to "
        "the next map wipe, with a configurable message and a chat "
        "command to check it. Reads the schedule from the config file.",
        "Install: drop WipeCountdown.cs into oxide/plugins, set your wipe "
        "date in the config, reload.",
        "Sample licence — this is demo data, not a real product.",
        "Sample support text — this is demo data, not a real product.",
    ),
    (
        "GatherBoost", "gatherboost", "Plugins", 499, "1.0.3", "Oxide · Carbon",
        "HA1FAL1VE", 0, 0, "passed", "2026-10-19", 445, 156, 18,
        "SAMPLE PLUGIN — fictional listing for demo purposes. Per-resource "
        "gather multipliers with VIP tiers and a weekend boost window. "
        "Set rates per item, per permission group, or globally — no "
        "server restart needed, changes apply on config reload.",
        "Install: drop GatherBoost.cs into oxide/plugins, edit the "
        "multipliers in the config, reload.",
        "Sample licence — this is demo data, not a real product.",
        "Sample support text — this is demo data, not a real product.",
    ),
    (
        "DiscordLink", "discordlink", "Discord Bots", 0, "1.3.1", "Oxide",
        "Bxcas", 0, 0, "passed", "2026-11-01", 833, 421, 0,
        "SAMPLE BOT — fictional listing for demo purposes. Links your "
        "Rust server to Discord: player join/leave messages, chat relay "
        "both ways, wipe announcements, and a /players command. One bot, "
        "one config file, no separate server needed.",
        "Install: create a Discord bot, paste the token into the config, "
        "drop DiscordLink.cs into oxide/plugins, reload.",
        "Sample licence — this is demo data, not a real product.",
        "Sample support text — this is demo data, not a real product.",
    ),
    (
        "KitManager Pro", "kitmanager-pro", "Plugins", 1299, "3.0.1",
        "Oxide · Carbon", "Razor", 0, 0, "passed", "2026-11-06", 912, 267, 44,
        "SAMPLE PLUGIN — fictional listing for demo purposes. Kits with "
        "cooldowns, permission tiers, kit previews, and a GUI players "
        "actually enjoy using. Import kits from a JSON file, set costs "
        "in scrap, and limit kits per wipe.",
        "Install: drop KitManagerPro.cs into oxide/plugins, import your "
        "kits from the example JSON, reload.",
        "Sample licence — this is demo data, not a real product.",
        "Sample support text — this is demo data, not a real product.",
    ),
    (
        "HeliEvents", "helievents", "Plugins", 799, "1.1.0", "Oxide",
        "HA1FAL1VE", 0, 0, "failed", "2026-11-04", 301, 88, 9,
        "SAMPLE PLUGIN — fictional listing for demo purposes. Scheduled "
        "attack-helicopter events with a warning siren, a loot crate on "
        "kill, and a configurable flight path. The last compile check "
        "FAILED (see the Versions tab) — the 1.1.0 file is held back "
        "until the author fixes it. Version 1.0.2 still downloads.",
        "Install: drop HeliEvents.cs into oxide/plugins, set the event "
        "schedule in the config, reload. Note the failed compile check "
        "on 1.1.0 — use 1.0.2 for now.",
        "Sample licence — this is demo data, not a real product.",
        "Sample support text — this is demo data, not a real product.",
    ),
    (
        "ServerPanel Lite", "serverpanel-lite", "Tools", 0, "0.9.4", "Oxide",
        "Bxcas", 0, 1, "pending", None, 156, 41, 0,
        "SAMPLE TOOL — fictional listing for demo purposes. A tiny web "
        "admin panel for your Rust server: players online, console, "
        "restart and wipe buttons, and a plugin list. Beta — expect rough "
        "edges. This is the sample listing that shows the WIP badge.",
        "Install: run the panel next to your server container, point it "
        "at your RCON details in the config, open the port.",
        "Sample licence — this is demo data, not a real product.",
        "Sample support text — this is demo data, not a real product.",
    ),
]

# listing slug -> [(version, changelog, compile_status, compile_date)]
VERSIONS = {
    "weightplus": [
        ("2.0.6", "Latest from the June 2025 build thread. HUD rework; "
         "encumbrance thresholds tuned. No successful compile shown yet.",
         "pending", None),
        ("2.0.5", "Slowdown via player input handling; UI layer fixes.",
         "pending", None),
    ],
    "autowipe-lgsm": [
        ("1.0.0", "Public-ready cleanup: idempotency fix, seed crash fix, "
         "early state write, cron overlap guard, examples folder.",
         "passed", "2026-07-03"),
    ],
    "raidalarm": [
        ("1.4.2", "Quiet-hours window and per-team pings.", "passed", "2026-11-05"),
        ("1.4.1", "Cooldown fixes.", "passed", "2026-10-22"),
    ],
    "abandoned-factory": [
        ("1.2.0", "Rooftop heli pad and new loot rooms.", "passed", "2026-10-28"),
        ("1.1.0", "NPC scientist spawns.", "passed", "2026-10-11"),
    ],
    "helievents": [
        ("1.1.0", "HELD BACK — compile check failed Nov 4, 2026.",
         "failed", "2026-11-04"),
        ("1.0.2", "Stable release. Use this one.", "passed", "2026-10-20"),
    ],
}

# listing slug -> [(username, rating, body)]
REVIEWS = {
    "weightplus": [
        ("Razor", 4, "The HUD idea is solid and the encumbrance thresholds "
         "feel right. Waiting on a working compile before I run it live."),
    ],
    "autowipe-lgsm": [
        ("Bxcas", 5, "Ran the July wipe with this after the cron miss. "
         "Idempotent re-runs saved me from a double wipe."),
        ("Razor", 5, "Clean config schema and the examples folder actually "
         "help. Does exactly what it says."),
    ],
    "raidalarm": [
        ("Bxcas", 5, "Alerts land in Discord within a second of the first "
         "explosive. Quiet hours work as advertised."),
        ("HA1FAL1VE", 4, "Good, but I want per-monument filtering. "
         "Author says it is coming."),
    ],
    "abandoned-factory": [
        ("HA1FAL1VE", 5, "Our players love the factory. Loot balance is "
         "fair and the parkour routes are fun."),
    ],
    "kitmanager-pro": [
        ("Bxcas", 5, "Best kit GUI I have used. Import from JSON just works."),
    ],
    "gatherboost": [
        ("Razor", 4, "Weekend boost window is a nice touch. Does the job."),
    ],
    "discordlink": [
        ("HA1FAL1VE", 5, "Chat relay both ways with zero fuss. Set it up "
         "in ten minutes."),
    ],
}

# listing slug -> [(username, body)]
COMMENTS = {
    "weightplus": [
        ("Razor", "Any update on the compile errors from the June thread?"),
        ("Realiztik", "Still working through them — the slowdown approach "
         "keeps fighting the movement code. v2.0.6 is the latest."),
    ],
    "autowipe-lgsm": [
        ("Bxcas", "Does this handle blueprint wipes separately from map "
         "wipes?"),
        ("Realiztik", "Yes — map and BP wipes are separate settings in "
         "wipe_config.json."),
    ],
    "raidalarm": [
        ("HA1FAL1VE", "Does this work with Carbon too?"),
        ("Razor", "Yes, 1.4.x runs on both Oxide and Carbon."),
    ],
}

EVENTS = [
    ("published", "Razor published RaidAlarm"),
    ("purchase", "Bxcas purchased Abandoned Factory"),
    ("review", "HA1FAL1VE reviewed DiscordLink — 5 stars"),
    ("published", "Razor updated KitManager Pro to 3.0.1"),
    ("purchase", "Razor purchased GatherBoost"),
    ("review", "Bxcas reviewed AutoWipe_LGSM — 5 stars"),
    ("published", "Bxcas published ServerPanel Lite"),
    ("download", "HA1FAL1VE downloaded WipeCountdown"),
]


def seed() -> None:
    conn = connect()
    try:
        user_ids = {}
        for username, email, bio in SAMPLE_USERS:
            cur = conn.execute(
                "INSERT INTO users (username, email, bio, is_sample) "
                "VALUES (?, ?, ?, 1)",
                (username, email, bio),
            )
            user_ids[username] = cur.lastrowid

        for row in LISTINGS:
            (title, slug, category, price, version, compat, seller,
             featured, is_wip, compile_status, compile_date, views,
             downloads, purchases, desc, docs, lic, support) = row
            cur = conn.execute(
                """INSERT INTO listings
                   (title, slug, description, docs, license_text,
                    support_text, price_cents, category, game, version,
                    compatibility, seller_id, status, featured, is_wip,
                    compile_status, compile_date, views, downloads,
                    purchases_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'rust', ?, ?, ?, 'approved',
                           ?, ?, ?, ?, ?, ?, ?)""",
                (title, slug, desc, docs, lic, support, price, category,
                 version, compat, user_ids[seller], featured, is_wip,
                 compile_status, compile_date, views, downloads, purchases),
            )
            listing_id = cur.lastrowid
            for version, changelog, cstatus, cdate in VERSIONS.get(slug, []):
                conn.execute(
                    """INSERT INTO versions
                       (listing_id, version, changelog, compile_status,
                        compile_date) VALUES (?, ?, ?, ?, ?)""",
                    (listing_id, version, changelog, cstatus, cdate),
                )
            for username, rating, body in REVIEWS.get(slug, []):
                conn.execute(
                    "INSERT INTO reviews (listing_id, user_id, rating, body)"
                    " VALUES (?, ?, ?, ?)",
                    (listing_id, user_ids[username], rating, body),
                )
            for username, body in COMMENTS.get(slug, []):
                conn.execute(
                    "INSERT INTO comments (listing_id, user_id, body)"
                    " VALUES (?, ?, ?)",
                    (listing_id, user_ids[username], body),
                )

        # Recompute rating averages from the seeded reviews.
        for row in conn.execute(
            "SELECT listing_id, AVG(rating) AS avg FROM reviews GROUP BY listing_id"
        ):
            conn.execute(
                "UPDATE listings SET rating_avg = ? WHERE id = ?",
                (row["avg"], row["listing_id"]),
            )

        for kind, text in EVENTS:
            conn.execute(
                "INSERT INTO events (kind, text) VALUES (?, ?)", (kind, text)
            )

        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES "
            "('site_name', 'The Rusting Dead Mod Marketplace'),"
            "('discord_invite_url', ''),"
            "('discord_online', '0'),"
            "('discord_members', '0')"
        )
        conn.commit()
    finally:
        conn.close()
