"""
Tests for BusinessProcessRegistry and process definitions.
"""

from app.domain.intents.classification.models import BusinessDomain
from app.domain.intents.classification.process.models import BusinessProcessDefinition
from app.domain.intents.classification.process.registry import BusinessProcessRegistry


def test_business_process_registry_defaults():
    registry = BusinessProcessRegistry()

    proc = registry.get("SALES_QUALIFICATION")
    assert proc is not None
    assert proc.process_id == "SALES_QUALIFICATION"
    assert proc.business_domain == BusinessDomain.CROSS_INDUSTRY
    assert proc.sla_target_hours == 4.0


def test_business_process_registration_and_listing():
    registry = BusinessProcessRegistry()

    custom_proc = BusinessProcessDefinition(
        process_id="CUSTOM_ENTERPRISE_ONBOARDING",
        name="Enterprise Client Onboarding",
        description="Complex enterprise contract signing and security verification.",
        business_domain=BusinessDomain.TECHNOLOGY,
        sla_target_hours=72.0,
        stages=["LEGAL_REVIEW", "SECURITY_AUDIT", "PROVISIONING"],
    )
    registry.register(custom_proc)

    fetched = registry.get("CUSTOM_ENTERPRISE_ONBOARDING")
    assert fetched == custom_proc
    assert fetched.sla_target_hours == 72.0
    assert len(registry.list_all()) >= 8
