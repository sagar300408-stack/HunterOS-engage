import pytest
import uuid
from datetime import datetime, timezone
from app.events.idempotency.hasher import CanonicalHasher
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.categories import EventCategory

def test_o4_notification_idempotency_ignores_transient_fields():
    # Prove that the exact same business event generated twice yields the same hash,
    # despite differing event_id and occurred_at
    
    correlation_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    
    event1 = {
        "event_id": uuid.uuid4(),
        "occurred_at": datetime.now(timezone.utc),
        "correlation_id": correlation_id,
        "workspace_id": workspace_id,
        "actor_type": "system",
        "category": "SCHEDULING",
        "customer_phone": "1234567890",
        "scheduled_for": "10:00 AM"
    }
    
    event2 = {
        "event_id": uuid.uuid4(),
        "occurred_at": datetime.now(timezone.utc),
        "correlation_id": correlation_id,
        "workspace_id": workspace_id,
        "actor_type": "system",
        "category": "SCHEDULING",
        "customer_phone": "1234567890",
        "scheduled_for": "10:00 AM"
    }
    
    # Event 1 hash
    hash1 = CanonicalHasher.hash_event_domain_payload(event1)
    
    # Event 2 hash
    hash2 = CanonicalHasher.hash_event_domain_payload(event2)
    
    assert hash1 == hash2, "O4 PROOF FAILED: Different transient fields caused different hashes."
    
    # Prove that changing a business field changes the hash
    event3 = {
        "event_id": uuid.uuid4(),
        "occurred_at": datetime.now(timezone.utc),
        "correlation_id": correlation_id,
        "workspace_id": workspace_id,
        "actor_type": "system",
        "category": "SCHEDULING",
        "customer_phone": "1234567890",
        "scheduled_for": "11:00 AM"
    }
    
    hash3 = CanonicalHasher.hash_event_domain_payload(event3)
    
    assert hash1 != hash3, "O4 PROOF FAILED: Changed payload did not change hash."
