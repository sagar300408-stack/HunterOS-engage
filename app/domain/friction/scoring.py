"""
FrictionScoreEngine
────────────────────
Computes the Business Friction Score (BFS) — a weighted 0–100 index.

Higher score = more friction = business needs attention.
Contributors are aggregated from open FrictionEvent records.

Scoring model:
  Each friction type has a max weight (sum = 100).
  Actual contribution = min(open_count × per_event_weight, max_weight).
  Final BFS = sum of all capped contributions.
"""
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID

from app.domain.friction.models import (
    FrictionEvent, FrictionType, FrictionScoreSnapshot
)
from app.domain.friction.repository import FrictionRepository


# Weight configuration: friction_type → (max_contribution, per_event_points)
WEIGHT_CONFIG: Dict[str, tuple] = {
    FrictionType.LEAD_RESPONSE_DELAY.value:  (20, 4.0),
    FrictionType.MISSED_FOLLOWUP.value:      (15, 3.0),
    FrictionType.SLA_VIOLATION.value:        (15, 5.0),
    FrictionType.APPROVAL_DELAY.value:       (15, 6.0),
    FrictionType.WORKFLOW_STALL.value:       (15, 5.0),
    FrictionType.CUSTOMER_INACTIVITY.value:  (10, 2.0),
    FrictionType.OPPORTUNITY_LEAKAGE.value:  (10, 3.0),
}


class FrictionScoreEngine:
    """Computes and persists the Business Friction Score."""

    def __init__(self, repo: FrictionRepository):
        self.repo = repo

    async def compute_score(self, workspace_id: UUID) -> FrictionScoreSnapshot:
        """
        Aggregate open FrictionEvents by type, apply weights,
        compute final 0–100 score, and return a snapshot.
        """
        open_by_type = await self.repo.get_open_events_by_type(workspace_id)
        previous     = await self.repo.get_latest_score(workspace_id)

        contributors: Dict[str, float] = {}
        total_score = 0.0

        for ftype, (max_weight, per_event) in WEIGHT_CONFIG.items():
            count        = open_by_type.get(ftype, 0)
            contribution = min(count * per_event, float(max_weight))
            if contribution > 0:                        # only record active sources
                contributors[ftype] = round(contribution, 2)
            total_score += contribution

        # Also add raw score_contribution from events not in config
        for ftype, count in open_by_type.items():
            if ftype not in WEIGHT_CONFIG:
                capped = min(count * 2.0, 5.0)
                if capped > 0:
                    contributors[ftype] = round(capped, 2)
                total_score += capped

        final_score = round(min(total_score, 100.0), 2)
        prev_score  = previous.score if previous else None
        delta       = round(final_score - prev_score, 2) if prev_score is not None else None

        # Determine trend
        if delta is None or abs(delta) < 1.0:
            trend = "STABLE"
        elif delta > 0:
            trend = "DETERIORATING"
        else:
            trend = "IMPROVING"

        return FrictionScoreSnapshot(
            workspace_id=workspace_id,
            score=final_score,
            previous_score=prev_score,
            score_delta=delta,
            contributors=contributors,
            trend=trend,
            calculated_at=datetime.now(timezone.utc),
        )
