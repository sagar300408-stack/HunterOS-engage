import pytest
from app.domain.recommendations.models import RecommendationType
from app.domain.operations.models import ActionType
from app.domain.operations.intelligence.registry import ActionCapabilityRegistry

def test_capability_mapping_supported_types():
    assert ActionCapabilityRegistry.is_supported(RecommendationType.FOLLOW_UP)
    assert ActionCapabilityRegistry.get_supported_action(RecommendationType.FOLLOW_UP) == ActionType.CREATE_FOLLOWUP

    assert ActionCapabilityRegistry.is_supported(RecommendationType.CONTACT_CUSTOMER)
    assert ActionCapabilityRegistry.get_supported_action(RecommendationType.CONTACT_CUSTOMER) == ActionType.SEND_MESSAGE

    assert ActionCapabilityRegistry.is_supported(RecommendationType.SCHEDULE_SITE_VISIT)
    assert ActionCapabilityRegistry.get_supported_action(RecommendationType.SCHEDULE_SITE_VISIT) == ActionType.SCHEDULE_SITE_VISIT

def test_capability_mapping_unsupported_types():
    # Unsupported types should explicitly return False and None
    unsupported_types = [
        RecommendationType.DISCUSS_PRICING,
        RecommendationType.PROPERTY_ALTERNATIVE,
        RecommendationType.CUSTOM,
    ]
    for r_type in unsupported_types:
        assert not ActionCapabilityRegistry.is_supported(r_type)
        assert ActionCapabilityRegistry.get_supported_action(r_type) is None

def test_no_dynamic_generation():
    # Registry should be tightly constrained to explicit _mappings
    assert len(ActionCapabilityRegistry._mappings) == 3
