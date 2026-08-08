from __future__ import annotations
from typing import Dict, Any, List, Optional
from app.domain.journey.models import JourneyState, JourneyStageTransition
from app.domain.journey.maturity.models import JourneyMaturityResult

class SalesJourneyView:
    @staticmethod
    def render(
        journey_state: JourneyState,
        transitions: List[JourneyStageTransition],
        maturity_result: Optional[JourneyMaturityResult] = None,
    ) -> Dict[str, Any]:
        commercial_evidence = []
        for t in transitions:
            for ev in t.evidence:
                ev_type_val = ev.evidence_type.value if hasattr(ev.evidence_type, 'value') else ev.evidence_type
                if ev_type_val == 'INTENT':
                    commercial_evidence.append({
                        "evidence_id": ev.evidence_id,
                        "description": ev.description,
                        "timestamp": ev.timestamp
                    })
        
        observed_progression = [
            {
                "from": t.from_stage.value if hasattr(t.from_stage, 'value') else t.from_stage,
                "to": t.to_stage.value if hasattr(t.to_stage, 'value') else t.to_stage,
                "occurred_at": t.occurred_at
            }
            for t in sorted(transitions, key=lambda x: x.occurred_at)
        ]
        
        view: Dict[str, Any] = {
            "current_stage": journey_state.current_stage.value if hasattr(journey_state.current_stage, 'value') else journey_state.current_stage,
            "previous_stage": journey_state.previous_stage.value if hasattr(journey_state.previous_stage, 'value') and journey_state.previous_stage else journey_state.previous_stage,
            "stage_history": [s.value if hasattr(s, 'value') else s for s in journey_state.stage_history],
            "commercial_evidence": commercial_evidence,
            "observed_progression": observed_progression
        }

        if maturity_result is not None:
            view["maturity_score"] = maturity_result.maturity.maturity_score
            view["maturity_level"] = maturity_result.maturity.maturity_level.value
            view["momentum_state"] = maturity_result.momentum.state.value
            view["momentum_description"] = maturity_result.momentum.description
            view["stage_velocity_state"] = maturity_result.velocity.velocity_state.value
            view["current_residency_days"] = maturity_result.current_residency.duration_days
            view["observed_probability"] = (
                maturity_result.observed_probability.value
                if maturity_result.observed_probability
                else None
            )

        return view
