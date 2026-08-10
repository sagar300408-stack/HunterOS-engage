from __future__ import annotations
import pytest
from dataclasses import FrozenInstanceError

def test_identity_fields_immutable(recommendation):
    with pytest.raises(FrozenInstanceError):
        recommendation.id = "new_id"
