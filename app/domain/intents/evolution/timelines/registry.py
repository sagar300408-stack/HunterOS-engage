"""
HunterOS Engage V1 - Intent Timeline Registry
Extensible registry providing domain-specific timeline projections per entity type.
"""

from __future__ import annotations

import threading
from typing import Dict, Optional

from app.domain.intents.evolution.models import EntityType
from app.domain.intents.evolution.timelines.base import AbstractTimelineBuilder
from app.domain.intents.evolution.timelines.customer import CustomerTimelineBuilder
from app.domain.intents.evolution.timelines.deal import DealTimelineBuilder
from app.domain.intents.evolution.timelines.organization import OrganizationTimelineBuilder


class IntentTimelineRegistry:
    """
    Thread-safe registry mapping EntityTypes to dedicated AbstractTimelineBuilders.
    """

    def __init__(self, register_defaults: bool = True):
        self._builders: Dict[EntityType, AbstractTimelineBuilder] = {}
        self._lock = threading.RLock()

        if register_defaults:
            self._register_default_builders()

    def _register_default_builders(self) -> None:
        """Register default entity timeline builders."""
        self.register(CustomerTimelineBuilder())
        self.register(OrganizationTimelineBuilder())
        self.register(DealTimelineBuilder(EntityType.DEAL))
        self.register(DealTimelineBuilder(EntityType.OPPORTUNITY))
        self.register(CustomerTimelineBuilder()) # Fallback for others

    def register(self, builder: AbstractTimelineBuilder) -> None:
        """Register a timeline builder for an entity type."""
        with self._lock:
            self._builders[builder.entity_type] = builder

    def get_builder(self, entity_type: EntityType) -> AbstractTimelineBuilder:
        """Retrieve appropriate builder with automatic customer fallback."""
        with self._lock:
            if entity_type in self._builders:
                return self._builders[entity_type]
            # Fallback to customer builder
            return self._builders.get(EntityType.CUSTOMER, CustomerTimelineBuilder())


default_timeline_registry = IntentTimelineRegistry()
