"""
HunterOS Engage V1 - Manufacturing Industry Plugin
"""

from __future__ import annotations

from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
)
from app.domain.intents.classification.plugins.base import IndustryIntentPlugin
from app.domain.intents.classification.process.models import BusinessProcessDefinition
from app.domain.intents.classification.taxonomy.models import (
    TaxonomyEdge,
    TaxonomyNode,
)


def create_manufacturing_plugin() -> IndustryIntentPlugin:
    nodes = [
        TaxonomyNode(
            node_id="commercial.rfp_procurement",
            category=IntentCategory.COMMERCIAL,
            display_name="RFP Procurement",
            description="B2B volume purchase, supplier bid, or manufacturing spec inquiry.",
            business_domain=BusinessDomain.MANUFACTURING,
            default_process="MANUFACTURING_PROCUREMENT",
            aliases=["RFP_INQUIRY", "SUPPLIER_BID"],
        ),
    ]
    edges = [
        TaxonomyEdge(source_node_id="commercial", target_node_id="commercial.rfp_procurement"),
    ]
    processes = [
        BusinessProcessDefinition(
            process_id="MANUFACTURING_PROCUREMENT",
            name="Manufacturing Procurement",
            description="Handling RFP, quote bids, material specifications, and batch lead times.",
            business_domain=BusinessDomain.MANUFACTURING,
            sla_target_hours=48.0,
        )
    ]
    return IndustryIntentPlugin(
        plugin_id="manufacturing",
        name="Manufacturing Industry Plugin",
        version="1.0.0",
        description="Manufacturing B2B procurement taxonomy and workflow definitions.",
        business_domain=BusinessDomain.MANUFACTURING,
        taxonomy_nodes=nodes,
        taxonomy_edges=edges,
        business_processes=processes,
    )
