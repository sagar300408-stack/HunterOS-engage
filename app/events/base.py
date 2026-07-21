"""
TOMBSTONED: This file is deprecated as of HunterOS Phase 7 Architecture Realignment.
Please use `app.events.model.base_event.UniversalBaseEvent` instead.
"""
from app.events.model.base_event import UniversalBaseEvent

class BaseEvent:
    def __init__(self, *args, **kwargs):
        import warnings
        warnings.warn("BaseEvent is deprecated. Use UniversalBaseEvent instead.", DeprecationWarning, stacklevel=2)
