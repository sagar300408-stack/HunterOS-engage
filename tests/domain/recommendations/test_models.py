from __future__ import annotations
import pytest
from dataclasses import FrozenInstanceError

def test_recommendation_immutability(recommendation):
    with pytest.raises(FrozenInstanceError):
        recommendation.score = 0.5
