"""
HunterOS Engage — Event Schema Versioning Package
app/events/schema/__init__.py

Exports the module-level schema_registry singleton used throughout the
application for version registration, adapter lookup, and payload upgrade.

Usage:
    from app.events.schema import schema_registry

    # Register an upgrade adapter (typically in app/events/schema/adapters.py)
    @schema_registry.adapter("RawWebhookEvent", from_version=1, to_version=2)
    def upgrade_raw_webhook_v1_to_v2(payload: dict) -> dict:
        payload.setdefault("source_channel", "meta_webhook")
        return payload

    # At dispatch time (handled automatically by tasks.py)
    upgraded = schema_registry.upgrade_payload("RawWebhookEvent", payload, stored_version=1)
"""

from app.events.schema.registry import (
    SchemaRegistry,
    SchemaValidationError,
    SchemaValidationFailed,
)

# Module-level singleton — imported by tasks.py, bootstrap, and adapter modules
schema_registry = SchemaRegistry()

__all__ = [
    "schema_registry",
    "SchemaRegistry",
    "SchemaValidationError",
    "SchemaValidationFailed",
]
