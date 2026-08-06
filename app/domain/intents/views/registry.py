"""
HunterOS Engage V1 - Intent View Registry
Thread-safe registry for intent view projections.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from app.domain.intents.views.base import AbstractIntentView
from app.domain.intents.views.standard import (
    AuditIntentView,
    ExecutiveIntentView,
    OperationsIntentView,
    SalesIntentView,
)


class IntentViewRegistry:
    """Registry managing available multi-perspective intent views."""

    def __init__(self, register_defaults: bool = True):
        self._lock = threading.RLock()
        self._views: Dict[str, AbstractIntentView] = {}

        if register_defaults:
            self.register_view(ExecutiveIntentView())
            self.register_view(SalesIntentView())
            self.register_view(OperationsIntentView())
            self.register_view(AuditIntentView())

    def register_view(self, view: AbstractIntentView) -> None:
        with self._lock:
            self._views[view.view_name.lower()] = view

    def get_view(self, view_name: str) -> Optional[AbstractIntentView]:
        with self._lock:
            return self._views.get(view_name.lower())

    def list_views(self) -> List[AbstractIntentView]:
        with self._lock:
            return list(self._views.values())


# Default instance
default_intent_view_registry = IntentViewRegistry(register_defaults=True)
