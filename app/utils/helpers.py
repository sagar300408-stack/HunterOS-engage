"""Utility helpers for HunterOS Engage."""

from datetime import datetime, timezone
from typing import Optional


def normalize_phone(phone: str) -> str:
    """Strip all non-digit characters from a phone number string."""
    return "".join(filter(str.isdigit, phone))


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    from app.utils.clock import SystemClock
    return SystemClock.now()


def extract_message_data(payload: dict) -> Optional[dict]:
    """
    Extract relevant fields from a Meta WhatsApp webhook payload.

    Returns a dict with:
        wa_message_id, from_phone, content, timestamp, contact_name

    Returns None if:
        - The payload does not contain messages
        - The message type is not "text"
        - The payload structure is malformed
    """
    try:
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return None

        message = value["messages"][0]
        contacts = value.get("contacts", [{}])
        contact = contacts[0] if contacts else {}

        if message.get("type") != "text":
            return None

        return {
            "wa_message_id": message["id"],
            "from_phone": normalize_phone(message["from"]),
            "content": message["text"]["body"],
            "timestamp": datetime.fromtimestamp(
                int(message["timestamp"]), tz=timezone.utc
            ),
            "contact_name": contact.get("profile", {}).get("name", "Unknown"),
        }

    except (KeyError, IndexError, TypeError, ValueError):
        return None
