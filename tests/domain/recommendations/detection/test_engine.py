import pytest
from app.domain.recommendations.detection.engine import RecommendationDetectionEngine

class MockContextProvider:
    def load(self, w_id, target):
        return {"raw": True}
    def normalize(self, context):
        return {"normalized": True}

class MockRule:
    def evaluate(self, context):
        class Candidate:
            def __init__(self):
                self.triggers = ["t1"]
                self.evidence = ["e1"]
                self.recommendation_type = "FOLLOW_UP"
                self.target_id = "123"
        return [Candidate()]

class MockRuleRegistry:
    def get_applicable_rules(self, context):
        return [MockRule()]

def test_engine_detect():
    engine = RecommendationDetectionEngine()
    result = engine.detect("w_id", "target", MockContextProvider(), MockRuleRegistry())
    assert result.workspace_id == "w_id"
    assert len(result.candidates) == 1
    assert result.candidates[0].recommendation_type == "FOLLOW_UP"
