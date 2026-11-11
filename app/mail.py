"""Optional email notifications via SMTP.

All settings come from the environment (SMTP_HOST, SMTP_PORT, SMTP_USER,
SMTP_PASS, SMTP_FROM). If SMTP is not configured, send() simply returns
False and the site works fully without email — nothing is logged and
nothing is sent anywhere. Callers must never let a mail failure break a
request: wrap calls in try/except or rely on send() swallowing errors.
"""
import os
import smtplib
import ssl
from email.message import EmailMessage


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST"))


def send(to: str, subject: str, body: str) -> bool:
    """Send one plain-text email. Returns True if it was accepted by the
    SMTP server, False otherwise (including 'not configured')."""
    host = os.environ.get("SMTP_HOST", "")
    if not host or not to:
        return False
    port = int(os.environ.get("SMTP_PORT", "587") or 587)
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    sender = os.environ.get("SMTP_FROM", user or "noreply@localhost")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=context,
                                  timeout=15) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if user:
                    server.login(user, password)
                server.send_message(msg)
        return True
    except Exception:
        # Email is best-effort. Never crash a request over a mail failure,
        # and never log credentials or message bodies.
        return False
