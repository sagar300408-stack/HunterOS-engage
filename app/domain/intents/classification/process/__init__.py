"""
HunterOS Engage V1 - Business Process Subsystem
Dynamic process registry supporting cross-industry workflows without code modifications.
"""

from app.domain.intents.classification.process.models import BusinessProcessDefinition
from app.domain.intents.classification.process.registry import (
    BusinessProcessRegistry,
    default_business_process_registry,
)

__all__ = [
    "BusinessProcessDefinition",
    "BusinessProcessRegistry",
    "default_business_process_registry",
]
