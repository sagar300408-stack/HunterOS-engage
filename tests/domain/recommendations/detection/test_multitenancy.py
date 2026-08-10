import pytest

def test_multitenancy():
    from app.domain.recommendations.detection.engine import RecommendationDetectionEngine
    engine = RecommendationDetectionEngine()
    class MockContextProvider:
        def load(self, w_id, target): return {"w_id": w_id}
        def normalize(self, ctx): return ctx
    class MockRuleReg:
        def get_applicable_rules(self, ctx): return []
    
    res1 = engine.detect("w1", "t", MockContextProvider(), MockRuleReg())
    res2 = engine.detect("w2", "t", MockContextProvider(), MockRuleReg())
    assert res1.workspace_id == "w1"
    assert res2.workspace_id == "w2"
