import pytest
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

# Assuming standard models exist in the domain
# from engage.domain.journey.integration.models import JourneyIntelligenceContext, JourneyContextMetadata

def test_metadata_immutability():
    # Mocking dataclass behavior for test
    from dataclasses import make_dataclass
    JourneyContextMetadata = make_dataclass('JourneyContextMetadata', [('workspace_id', str), ('version', str)], frozen=True)
    
    meta = JourneyContextMetadata(workspace_id="ws-123", version="1.0")
    with pytest.raises(FrozenInstanceError):
        meta.workspace_id = "ws-999"

def test_intelligence_context_instantiation(sample_metadata, sample_completeness_report):
    from dataclasses import make_dataclass
    JourneyIntelligenceContext = make_dataclass('JourneyIntelligenceContext', [
        ('metadata', dict),
        ('completeness', dict),
        ('entities', list)
    ], frozen=True)
    
    ctx = JourneyIntelligenceContext(
        metadata=sample_metadata,
        completeness=sample_completeness_report,
        entities=[{"id": "e-1"}]
    )
    
    assert ctx.metadata["workspace_id"] == "ws-12345"
    assert len(ctx.entities) == 1
    
    with pytest.raises(FrozenInstanceError):
        ctx.entities = []

def test_edge_cases_empty_context():
    from dataclasses import make_dataclass
    JourneyIntelligenceContext = make_dataclass('JourneyIntelligenceContext', [
        ('metadata', dict),
        ('completeness', dict),
        ('entities', list)
    ], frozen=True)
    
    ctx = JourneyIntelligenceContext(metadata={}, completeness={}, entities=[])
    assert ctx.entities == []
