from __future__ import annotations
from typing import Dict, Any, List, Optional
from app.domain.journey.models import JourneyState, JourneyStageTransition, JourneyTimeline
from app.domain.journey.maturity.models import JourneyMaturityResult

class OperationsJourneyView:
    @staticmethod
    def render(
        journey_state: JourneyState,
        transitions: List[JourneyStageTransition],
        timeline: JourneyTimeline,
        maturity_result: Optional[JourneyMaturityResult] = None,
    ) -> Dict[str, Any]:
        scheduled_events = [
            {
                "event_id": e.event_id,
                "type": e.event_type.value if hasattr(e.event_type, 'value') else e.event_type,
                "timestamp": e.timestamp
            }
            for e in timeline.events if (hasattr(e.event_type, 'value') and e.event_type.value == 'SCHEDULED') or e.event_type == 'SCHEDULED'
        ]
        
        completed_events = [
            {
                "event_id": e.event_id,
                "type": e.event_type.value if hasattr(e.event_type, 'value') else e.event_type,
                "timestamp": e.timestamp
            }
            for e in timeline.events if (hasattr(e.event_type, 'value') and e.event_type.value == 'COMPLETED') or e.event_type == 'COMPLETED'
        ]
        
        evidenced_blockers = []
        for t in transitions:
            for ev in t.evidence:
                if "blocker" in ev.description.lower() or "delay" in ev.description.lower():
                    evidenced_blockers.append({
                        "evidence_id": ev.evidence_id,
                        "description": ev.description,
                        "timestamp": ev.timestamp
                    })
                    
        view: Dict[str, Any] = {
            "operational_stage": journey_state.current_stage.value if hasattr(journey_state.current_stage, 'value') else journey_state.current_stage,
            "scheduled_events": scheduled_events,
            "completed_events": completed_events,
            "evidenced_blockers": evidenced_blockers
        }

        if maturity_result is not None:
            view["velocity"] = {
                "transitions_per_week": maturity_result.velocity.transitions_per_week,
                "average_duration_days": maturity_result.velocity.average_stage_duration_days,
                "current_duration_days": maturity_result.velocity.current_stage_duration_days,
                "velocity_state": maturity_result.velocity.velocity_state.value,
            }
            view["stability"] = {
                "score": maturity_result.stability.stability_score,
                "level": maturity_result.stability.stability_level.value,
                "reentry_count": maturity_result.stability.stage_reentry_count,
            }
            view["stage_residencies"] = [
                {
                    "stage": r.stage.value,
                    "duration_days": r.duration_days,
                    "reentry_count": r.reentry_count,
                    "status": r.status.value,
                }
                for r in maturity_result.stage_residency
            ]

        return view
