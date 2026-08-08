from __future__ import annotations
import pytest
from app.domain.journey.evidence.collector import EvidenceCollector
from app.domain.journey.models import EvidenceType

@pytest.fixture
def collector():
    return EvidenceCollector()

def test_collect_from_intent_context_extracts_intents(collector):
    intent_context = {
        "detected_intents": [{"id": "1", "confidence": 0.9}],
        "classified_intents": [{"id": "2", "confidence": 0.8}]
    }
    evidence = collector.collect_from_intent_context(intent_context)
    assert len(evidence) == 2
    assert all(e.evidence_type == EvidenceType.INTENT for e in evidence)

def test_collect_from_conversation_context_extracts_topics(collector):
    conversation_context = {
        "insights": [{"id": "3", "confidence": 0.8}],
        "timeline_events": [{"id": "4"}]
    }
    evidence = collector.collect_from_conversation_context(conversation_context)
    assert len(evidence) == 2
    types = [e.evidence_type for e in evidence]
    assert EvidenceType.CONVERSATION in types
    assert EvidenceType.TIMELINE_EVENT in types

def test_collect_from_memory_context_is_optional(collector):
    evidence = collector.collect_from_memory_context(None)
    assert len(evidence) == 0
    
    memory_context = {"items": [{"id": "5"}]}
    evidence2 = collector.collect_from_memory_context(memory_context)
    assert len(evidence2) == 1
    assert evidence2[0].evidence_type == EvidenceType.MEMORY_CONTEXT

def test_collect_all_combines_all_sources(collector):
    intent_context = {"detected_intents": [{"id": "1"}]}
    conversation_context = {"insights": [{"id": "2"}]}
    memory_context = {"items": [{"id": "3"}]}
    
    evidence = collector.collect_all(intent_context, conversation_context, memory_context)
    assert len(evidence) == 3

def test_empty_contexts_return_empty_evidence(collector):
    evidence = collector.collect_all({}, {})
    assert len(evidence) == 0
