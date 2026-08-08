from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.domain.journey.models import JourneyState, JourneyDefinition, JourneyStageTransition
from app.domain.journey.maturity.models import JourneyMaturityResult

class ExecutiveJourneyView:
    @staticmethod
    def render(
        journey_state: JourneyState,
        journey_definition: JourneyDefinition,
        transitions: List[JourneyStageTransition],
        maturity_result: Optional[JourneyMaturityResult] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        stage_duration_days = (now - journey_state.stage_entered_at).days if journey_state.stage_entered_at else 0
        journey_age_days = (now - journey_state.journey_started_at).days if journey_state.journey_started_at else 0
        
        major_transitions = [
            {
                "from": t.from_stage.value if hasattr(t.from_stage, 'value') else t.from_stage,
                "to": t.to_stage.value if hasattr(t.to_stage, 'value') else t.to_stage,
                "date": t.occurred_at
            }
            for t in transitions if (hasattr(t.transition_type, 'value') and t.transition_type.value == 'MAJOR') or t.transition_type == 'MAJOR'
        ]
        
        view: Dict[str, Any] = {
            "current_stage": journey_state.current_stage.value if hasattr(journey_state.current_stage, 'value') else journey_state.current_stage,
            "journey_status": journey_state.status.value if hasattr(journey_state.status, 'value') else journey_state.status,
            "stage_duration_days": stage_duration_days,
            "transition_count": len(transitions),
            "journey_age_days": journey_age_days,
            "major_transitions": major_transitions
        }

        if maturity_result is not None:
            view["maturity_score"] = maturity_result.maturity.maturity_score
            view["maturity_level"] = maturity_result.maturity.maturity_level.value
            view["momentum_state"] = maturity_result.momentum.state.value
            view["stability_level"] = maturity_result.stability.stability_level.value
            view["journey_health"] = maturity_result.health.state.value
            view["observed_probability"] = (
                maturity_result.observed_probability.value
                if maturity_result.observed_probability
                else None
            )

        return view
