"""
TOMBSTONED: This file is deprecated as of HunterOS Phase 7 Architecture Realignment.
Please use `app.events.bus.event_bus.EventBus` instead.
"""

class DummyDispatcher:
    def subscribe(self, *args, **kwargs):
        import warnings
        warnings.warn("dispatcher.subscribe is deprecated. Use EventBus instead.", DeprecationWarning, stacklevel=2)
        
    async def dispatch(self, *args, **kwargs):
        import warnings
        warnings.warn("dispatcher.dispatch is deprecated. Use EventBus instead.", DeprecationWarning, stacklevel=2)

dispatcher = DummyDispatcher()
