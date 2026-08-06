"""
Tests for Classification Rules, Rule Registry, and Industry Intent Plugins.
"""

from app.domain.intents.classification.canonical.models import CanonicalIntent
from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
)
from app.domain.intents.classification.plugins.packs.real_estate import (
    create_real_estate_plugin,
)
from app.domain.intents.classification.plugins.registry import IndustryPluginRegistry
from app.domain.intents.classification.rules.packs.core import (
    PricingInquiryClassificationRule,
)


def test_core_pricing_rule():
    rule = PricingInquiryClassificationRule()
    canonical = CanonicalIntent(
        conversation_id="conv_rule_1",
        canonical_name="pricing_inquiry",
        normalized_title="cost and discount question",
        normalized_description="what is the total rate?",
        confidence=0.85,
    )
    context = IntentClassificationContext(conversation_id="conv_rule_1")

    candidate = rule.evaluate(canonical, context)
    assert candidate is not None
    assert candidate.category == IntentCategory.COMMERCIAL
    assert candidate.process == "SALES_QUALIFICATION"
    assert candidate.taxonomy_node_id == "commercial.pricing_inquiry"


def test_industry_plugin_registration():
    plugin_reg = IndustryPluginRegistry()
    re_plugin = create_real_estate_plugin()

    plugin_reg.register_plugin(re_plugin)

    # Check plugin retrieval
    fetched = plugin_reg.get_plugin("real_estate")
    assert fetched is not None
    assert fetched.business_domain == BusinessDomain.REAL_ESTATE
    assert len(fetched.taxonomy_nodes) >= 2
    assert len(fetched.business_processes) >= 1
