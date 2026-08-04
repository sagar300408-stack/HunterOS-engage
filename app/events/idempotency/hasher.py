"""
HunterOS Engage — Canonical Payload Hasher
app/events/idempotency/hasher.py

Provides deterministic canonical JSON serialization and SHA-256 payload hashing.
Guarantees identical hashes for semantically equivalent payloads regardless of
key ordering, formatting, or serialization quirks.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Union
from uuid import UUID

from pydantic import BaseModel


class CanonicalHasher:
    """
    Deterministic serializer and SHA-256 hasher for event payloads.
    """

    # Fields that represent ephemeral delivery/lifecycle identifiers rather than
    # domain event identity when hashing a UniversalBaseEvent directly.
    TRANSIENT_EVENT_FIELDS = frozenset({
        "event_id",
        "occurred_at",
        "metadata",
    })

    @classmethod
    def normalize_value(cls, val: Any) -> Any:
        """
        Recursively normalizes arbitrary Python objects into canonical primitives.
        """
        if val is None:
            return None
        if isinstance(val, (str, int, bool)):
            return val
        if isinstance(val, float):
            # Normalize negative zero and clean representation
            return 0.0 if val == 0.0 else val
        if isinstance(val, UUID):
            return str(val).lower()
        if isinstance(val, datetime):
            # Normalize to UTC ISO-8601 string
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
            else:
                val = val.astimezone(timezone.utc)
            return val.isoformat()
        if isinstance(val, date):
            return val.isoformat()
        if isinstance(val, Enum):
            return cls.normalize_value(val.value)
        if isinstance(val, BaseModel):
            return cls.normalize_value(val.model_dump())
        if isinstance(val, dict):
            # Recursively sort keys alphabetically
            return {
                str(k): cls.normalize_value(v)
                for k, v in sorted(val.items(), key=lambda item: str(item[0]))
            }
        if isinstance(val, (list, tuple, set)):
            # Preserves list ordering; normalizes each element
            return [cls.normalize_value(item) for item in val]
        # Fallback for other objects
        return str(val)

    @classmethod
    def to_canonical_json(cls, data: Any) -> str:
        """
        Converts data to deterministic, canonical JSON string.
        - UTF-8 encoding
        - No insignificant whitespace (separators=(',', ':'))
        - Recursive sorted keys
        """
        normalized = cls.normalize_value(data)
        return json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    @classmethod
    def hash_payload(cls, data: Any) -> str:
        """
        Computes SHA-256 hex digest of the canonical JSON representation of *data*.
        """
        canonical_str = cls.to_canonical_json(data)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @classmethod
    def hash_event_domain_payload(cls, event: Any) -> str:
        """
        Extracts domain-specific data from an event (excluding transient event_id,
        occurred_at, metadata) and returns its canonical SHA-256 hash.
        """
        if isinstance(event, BaseModel):
            dump = event.model_dump()
            domain_data = {
                k: v for k, v in dump.items()
                if k not in cls.TRANSIENT_EVENT_FIELDS
            }
            return cls.hash_payload(domain_data)
        elif isinstance(event, dict):
            domain_data = {
                k: v for k, v in event.items()
                if k not in cls.TRANSIENT_EVENT_FIELDS
            }
            return cls.hash_payload(domain_data)
        return cls.hash_payload(event)
