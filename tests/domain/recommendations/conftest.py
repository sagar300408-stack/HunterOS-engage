from __future__ import annotations
import pytest
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass

class RecommendationTarget:
    def __init__(self, id, type):
        self.id = id
        self.type = type

class RecommendationContext:
    def __init__(self, timestamp):
        self.timestamp = timestamp

@dataclass(frozen=True)
class Recommendation:
    id: uuid.UUID
    workspace_id: uuid.UUID
    target: RecommendationTarget
    context: RecommendationContext
    score: float
    status: str

@pytest.fixture
def workspace_id():
    return uuid.uuid4()

@pytest.fixture
def recommendation(workspace_id):
    return Recommendation(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        target=RecommendationTarget(id="user_1", type="user"),
        context=RecommendationContext(timestamp=datetime.now(timezone.utc)),
        score=0.99,
        status="generated"
    )
