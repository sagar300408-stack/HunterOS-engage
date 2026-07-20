import uuid
from typing import List
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.intelligence.models import PredictionEvent, OperationalHealthSnapshot


class PredictionEngine:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def run_predictions(self, workspace_id: uuid.UUID, current_health: OperationalHealthSnapshot) -> List[PredictionEvent]:
        """
        Extrapolates from current friction/health metrics to predict future state.
        """
        now = datetime.now(timezone.utc)
        predictions = []

        # Check existing valid predictions so we don't duplicate
        existing = await self.session.execute(
            select(PredictionEvent)
            .where(
                PredictionEvent.workspace_id == workspace_id,
                PredictionEvent.invalidated_at == None
            )
        )
        active_predictions = existing.scalars().all()

        has_sla_prediction = any(p.prediction_type == "SLA_BREACH_FORECAST" for p in active_predictions)

        # Basic Heuristic 1: If friction is rising rapidly, predict SLA breach
        if current_health.trend == "DETERIORATING" and current_health.friction_delta and current_health.friction_delta > 5.0:
            if not has_sla_prediction:
                pred = PredictionEvent(
                    workspace_id=workspace_id,
                    prediction_type="SLA_BREACH_FORECAST",
                    description="Current trend suggests Proposal delays will exceed SLA within 3 days.",
                    confidence_score=0.91,
                    timeframe_days=3,
                    predicted_impact="Revenue at Risk increases by ₹ 8.4 Lakhs",
                    created_at=now
                )
                self.session.add(pred)
                predictions.append(pred)

        # Basic Heuristic 2: Score extrapolation
        if current_health.friction_score > 30.0 and current_health.trend == "DETERIORATING":
            has_score_prediction = any(p.prediction_type == "SCORE_EXTRAPOLATION" for p in active_predictions)
            if not has_score_prediction:
                predicted_score = min(100.0, current_health.friction_score + (current_health.friction_delta or 5.0) * 3)
                pred = PredictionEvent(
                    workspace_id=workspace_id,
                    prediction_type="SCORE_EXTRAPOLATION",
                    description=f"Current trend suggests Business Friction will reach {round(predicted_score)} within 5 days.",
                    confidence_score=0.85,
                    timeframe_days=5,
                    created_at=now
                )
                self.session.add(pred)
                predictions.append(pred)

        # Invalidation logic: If trend is improving, invalidate negative predictions
        if current_health.trend == "IMPROVING":
            for p in active_predictions:
                if p.prediction_type in ["SLA_BREACH_FORECAST", "SCORE_EXTRAPOLATION"]:
                    p.invalidated_at = now

        return predictions
