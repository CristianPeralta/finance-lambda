"""
telegram.py — Telegram Bot API helpers for Lambda.
"""

import json
import os
import urllib.request


def _bot_url(method: str) -> str:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return f"https://api.telegram.org/bot{token}/{method}"


def send_message(chat_id, text: str, parse_mode: str = "Markdown") -> None:
    payload = json.dumps({
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": parse_mode,
    }).encode("utf-8")

    req = urllib.request.Request(
        _bot_url("sendMessage"),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


def reply(update: dict, text: str, parse_mode: str = "Markdown") -> None:
    """Send a message back to the chat that originated the update."""
    chat_id = update.get("message", {}).get("chat", {}).get("id")
    if chat_id:
        send_message(chat_id, text, parse_mode)


def notify(text: str) -> None:
    """Send a message to the chat configured in TELEGRAM_CHAT_ID (alerts and scheduled reports)."""
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    send_message(chat_id, text)
