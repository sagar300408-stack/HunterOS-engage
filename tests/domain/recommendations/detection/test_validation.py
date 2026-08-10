import pytest

def test_validation():
    from app.domain.recommendations.detection.engine import RecommendationDetectionEngine
    engine = RecommendationDetectionEngine()
    class Candidate:
        def __init__(self, t, e):
            self.triggers = t
            self.evidence = e
    c1 = Candidate(["t"], ["e"])
    c2 = Candidate([], ["e"])
    c3 = Candidate(["t"], [])
    valid = engine._validate([c1, c2, c3])
    assert len(valid) == 1
    assert valid[0].triggers == ["t"]
