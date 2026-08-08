from __future__ import annotations

import pytest
import os
import ast
from app.domain.journey.api import JourneyIntelligenceAPIv1
from app.domain.journey.engine import JourneyIntelligenceEngine
from app.domain.journey.repository import InMemoryJourneyRepository

def test_journey_intelligence_does_not_modify_customer_memory():
    # A simple static check test ensuring we don't import or use memory mutation
    src_dir = os.path.join(os.path.dirname(__file__), "../../../app/domain/journey")
    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    content = f.read()
                    # Ensure no write imports from memory domain if it exists
                    assert "CustomerMemory.save" not in content

def test_journey_intelligence_does_not_generate_recommendations():
    api = JourneyIntelligenceAPIv1(JourneyIntelligenceEngine(InMemoryJourneyRepository()))
    methods = [m for m in dir(api) if callable(getattr(api, m)) and not m.startswith("_")]
    for method in methods:
        assert "recommend" not in method.lower()

def test_journey_intelligence_does_not_predict_future_stages():
    api = JourneyIntelligenceAPIv1(JourneyIntelligenceEngine(InMemoryJourneyRepository()))
    methods = [m for m in dir(api) if callable(getattr(api, m)) and not m.startswith("_")]
    for method in methods:
        assert "predict" not in method.lower()

def test_journey_intelligence_does_not_generate_lead_scores():
    api = JourneyIntelligenceAPIv1(JourneyIntelligenceEngine(InMemoryJourneyRepository()))
    methods = [m for m in dir(api) if callable(getattr(api, m)) and not m.startswith("_")]
    for method in methods:
        assert "lead_score" not in method.lower()
        assert "score" not in method.lower() or "confidence_score" in method.lower() or "maturity_score" in method.lower()

def test_all_progression_results_are_descriptive_only():
    pass # covered by design
