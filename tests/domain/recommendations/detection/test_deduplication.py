import pytest

def test_deduplication():
    from app.domain.recommendations.detection.engine import RecommendationDetectionEngine
    engine = RecommendationDetectionEngine()
    class Candidate:
        def __init__(self, t, id):
            self.recommendation_type = t
            self.target_id = id
            
    c1 = Candidate("A", "1")
    c2 = Candidate("A", "1")
    c3 = Candidate("B", "1")
    c4 = Candidate("A", "2")
    
    deduped = engine._deduplicate([c1, c2, c3, c4])
    assert len(deduped) == 3
