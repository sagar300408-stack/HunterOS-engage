"""
HunterOS Engage V1 - Industry Intent Plugin Subsystem
Modular plugin architecture packaging taxonomy, rules, processes, relationships, and views per industry.
"""

from app.domain.intents.classification.plugins.base import IndustryIntentPlugin
from app.domain.intents.classification.plugins.registry import (
    IndustryPluginRegistry,
    default_industry_plugin_registry,
)

__all__ = [
    "IndustryIntentPlugin",
    "IndustryPluginRegistry",
    "default_industry_plugin_registry",
]
