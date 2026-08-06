"""
HunterOS Engage V1 - Real Estate Industry Plugin
"""

from __future__ import annotations

from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
)
from app.domain.intents.classification.plugins.base import IndustryIntentPlugin
from app.domain.intents.classification.process.models import BusinessProcessDefinition
from app.domain.intents.classification.rules.packs.real_estate import (
    RealEstateClassificationRulePack,
)
from app.domain.intents.classification.taxonomy.models import (
    TaxonomyEdge,
    TaxonomyNode,
)


def create_real_estate_plugin() -> IndustryIntentPlugin:
    nodes = [
        TaxonomyNode(
            node_id="information.property_inquiry",
            category=IntentCategory.INFORMATION,
            display_name="Property Inquiry",
            description="Inquiries regarding real estate units, configurations, and amenities.",
            business_domain=BusinessDomain.REAL_ESTATE,
            default_process="LEAD_CAPTURE",
            aliases=["PROPERTY_INQUIRY", "REAL_ESTATE_INQUIRY"],
        ),
        TaxonomyNode(
            node_id="operational.site_visit",
            category=IntentCategory.OPERATIONAL,
            display_name="Site Visit",
            description="Physical inspection or model apartment tour.",
            business_domain=BusinessDomain.REAL_ESTATE,
            default_process="APPOINTMENT_SCHEDULING",
            aliases=["SCHEDULE_SITE_VISIT", "SITE_VISIT"],
        ),
    ]
    edges = [
        TaxonomyEdge(source_node_id="information", target_node_id="information.property_inquiry"),
        TaxonomyEdge(source_node_id="operational", target_node_id="operational.site_visit"),
    ]
    processes = [
        BusinessProcessDefinition(
            process_id="PROPERTY_SALES_QUALIFICATION",
            name="Property Sales Qualification",
            description="Qualifying buyer preferences (BHK, budget, location, readiness to move).",
            business_domain=BusinessDomain.REAL_ESTATE,
            sla_target_hours=2.0,
        )
    ]
    return IndustryIntentPlugin(
        plugin_id="real_estate",
        name="Real Estate Industry Plugin",
        version="1.0.0",
        description="Comprehensive real estate intent taxonomy, rules, and property workflows.",
        business_domain=BusinessDomain.REAL_ESTATE,
        taxonomy_nodes=nodes,
        taxonomy_edges=edges,
        rule_pack=RealEstateClassificationRulePack(version="1.0.0"),
        business_processes=processes,
    )
