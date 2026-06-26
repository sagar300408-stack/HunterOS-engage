"""
Tests: Payload parsing utilities — extract_message_data, normalize_phone
"""

import pytest
from datetime import datetime, timezone

from app.utils.helpers import extract_message_data, normalize_phone


# ── normalize_phone ────────────────────────────────────────────────────────────

class TestNormalizePhone:
    def test_strips_plus(self):
        assert normalize_phone("+919876543210") == "919876543210"

    def test_strips_dashes_and_spaces(self):
        assert normalize_phone("+91-98765-43210") == "919876543210"

    def test_strips_parentheses(self):
        assert normalize_phone("(123) 456-7890") == "1234567890"

    def test_plain_digits_unchanged(self):
        assert normalize_phone("9876543210") == "9876543210"

    def test_empty_string(self):
        assert normalize_phone("") == ""


# ── extract_message_data ───────────────────────────────────────────────────────

VALID_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "entry_id",
            "changes": [
                {
                    "value": {
                        "messages": [
                            {
                                "id": "wamid.abc123",
                                "from": "919876543210",
                                "type": "text",
                                "timestamp": "1700000000",
                                "text": {"body": "Hello, I need help."},
                            }
                        ],
                        "contacts": [
                            {"profile": {"name": "Rajesh Kumar"}}
                        ],
                    }
                }
            ],
        }
    ],
}


class TestExtractMessageData:
    def test_valid_payload_extracts_all_fields(self):
        result = extract_message_data(VALID_PAYLOAD)
        assert result is not None
        assert result["wa_message_id"] == "wamid.abc123"
        assert result["from_phone"] == "919876543210"
        assert result["content"] == "Hello, I need help."
        assert result["contact_name"] == "Rajesh Kumar"
        assert isinstance(result["timestamp"], datetime)
        assert result["timestamp"].tzinfo == timezone.utc

    def test_non_text_message_returns_none(self):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.img",
                                        "from": "919876543210",
                                        "type": "image",
                                        "timestamp": "1700000000",
                                    }
                                ],
                                "contacts": [{"profile": {"name": "Test"}}],
                            }
                        }
                    ]
                }
            ]
        }
        assert extract_message_data(payload) is None

    def test_payload_without_messages_returns_none(self):
        payload = {
            "entry": [
                {"changes": [{"value": {"contacts": []}}]}
            ]
        }
        assert extract_message_data(payload) is None

    def test_empty_payload_returns_none(self):
        assert extract_message_data({}) is None

    def test_malformed_entry_returns_none(self):
        assert extract_message_data({"entry": []}) is None

    def test_phone_is_normalized(self):
        """Phone number with '+' prefix should be normalized to digits only."""
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.test",
                                        "from": "+91-98765-43210",
                                        "type": "text",
                                        "timestamp": "1700000000",
                                        "text": {"body": "Hi"},
                                    }
                                ],
                                "contacts": [{"profile": {"name": "Test"}}],
                            }
                        }
                    ]
                }
            ]
        }
        result = extract_message_data(payload)
        assert result is not None
        assert result["from_phone"] == "919876543210"

    def test_missing_contact_name_defaults_to_unknown(self):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.test",
                                        "from": "919876543210",
                                        "type": "text",
                                        "timestamp": "1700000000",
                                        "text": {"body": "Hi"},
                                    }
                                ],
                                "contacts": [{}],
                            }
                        }
                    ]
                }
            ]
        }
        result = extract_message_data(payload)
        assert result is not None
        assert result["contact_name"] == "Unknown"
