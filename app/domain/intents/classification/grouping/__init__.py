"""
HunterOS Engage V1 - Intent Grouping Subsystem
Aggregates classified intents into coherent functional clusters.
"""

from app.domain.intents.classification.grouping.engine import (
    IntentGroupingEngine,
    default_grouping_engine,
)
from app.domain.intents.classification.grouping.models import GroupAggregationReport

__all__ = [
    "GroupAggregationReport",
    "IntentGroupingEngine",
    "default_grouping_engine",
]
