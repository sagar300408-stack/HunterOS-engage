"""
HunterOS Engage — Deterministic Idempotency Key Generator
app/events/idempotency/generator.py

Generates collision-resistant, deterministic SHA-256 idempotency keys
for all events entering the HunterOS Event Pipeline.
"""

from __future__ import annotations

import hashlib
from typing import Any, Optional
from uuid import UUID

from app.events.idempotency.hasher import CanonicalHasher


class IdempotencyKeyGenerator:
    """
    Generates deterministic idempotency keys for UniversalBaseEvent instances.

    Composition:
        SHA-256(
            event_name +
            workspace_id +
            correlation_id +
            canonical_payload_hash
        )
    """

    def __init__(self, hasher: Optional[CanonicalHasher] = None) -> None:
        self._hasher = hasher or CanonicalHasher()

    def generate_key(
        self,
        event: Any,
        explicit_key: Optional[str] = None,
    ) -> str:
        """
        Derives a deterministic idempotency key for an event.

        If *explicit_key* is provided (or exists in event.metadata["idempotency_key"]),
        that key is preserved as an upstream transport identifier.
        """
        # 1. Check for explicit key
        if explicit_key:
            return explicit_key

        if hasattr(event, "metadata") and isinstance(event.metadata, dict):
            if "idempotency_key" in event.metadata and event.metadata["idempotency_key"]:
                return str(event.metadata["idempotency_key"])

        # 2. Extract key components
        event_name = getattr(event, "event_name", None) or (
            event.get("event_name") if isinstance(event, dict) else "unknown"
        )
        
        workspace_id = getattr(event, "workspace_id", None) or (
            event.get("workspace_id") if isinstance(event, dict) else ""
        )
        if isinstance(workspace_id, UUID):
            workspace_id = str(workspace_id).lower()
        else:
            workspace_id = str(workspace_id)

        correlation_id = getattr(event, "correlation_id", None) or (
            event.get("correlation_id") if isinstance(event, dict) else ""
        )
        if isinstance(correlation_id, UUID):
            correlation_id = str(correlation_id).lower()
        elif correlation_id is None:
            correlation_id = ""
        else:
            correlation_id = str(correlation_id)

        # 3. Compute canonical payload hash
        payload_hash = self._hasher.hash_event_domain_payload(event)

        # 4. Synthesize composite key
        composite = f"{event_name}:{workspace_id}:{correlation_id}:{payload_hash}"
        return hashlib.sha256(composite.encode("utf-8")).hexdigest()
