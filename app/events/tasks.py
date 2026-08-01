"""
app.events.tasks — REMOVED in Phase 1.3

This module has been deleted. All task definitions have moved to:

    app.events.worker.tasks      ← dispatch_event (Celery task)
    app.events.worker.maintenance ← recover_stale_events (Celery Beat task)

Any import from this module is a stale reference left over from Phase 1
and must be updated to point to the new location.
"""

raise ImportError(
    "app.events.tasks has been removed.\n"
    "Import dispatch_event from app.events.worker.tasks instead.\n"
    "Import recover_stale_events from app.events.worker.maintenance instead."
)

