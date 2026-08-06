"""
HunterOS Engage V1 - Cross Industry Plugin
"""

from __future__ import annotations

from app.domain.intents.classification.models import BusinessDomain
from app.domain.intents.classification.plugins.base import IndustryIntentPlugin
from app.domain.intents.classification.rules.packs.core import CoreClassificationRulePack


def create_cross_industry_plugin() -> IndustryIntentPlugin:
    return IndustryIntentPlugin(
        plugin_id="cross_industry",
        name="Cross-Industry Base Plugin",
        version="1.0.0",
        description="Foundational cross-industry intent rules, taxonomy, and processes.",
        business_domain=BusinessDomain.CROSS_INDUSTRY,
        rule_pack=CoreClassificationRulePack(version="1.0.0"),
    )
