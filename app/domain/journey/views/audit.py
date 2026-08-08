from __future__ import annotations
from typing import Dict, Any, List, Optional
from app.domain.journey.models import JourneyState, JourneyStageTransition, JourneyTimeline, JourneyDiagnostics
from app.domain.journey.maturity.models import JourneyMaturityResult

class AuditJourneyView:
    @staticmethod
    def render(
        journey_state: JourneyState,
        transitions: List[JourneyStageTransition],
        diagnostics_list: List[JourneyDiagnostics],
        timeline: JourneyTimeline,
        maturity_result: Optional[JourneyMaturityResult] = None,
    ) -> Dict[str, Any]:
        complete_transition_graph = [
            {
                "transition_id": t.transition_id,
                "from_stage": t.from_stage.value if hasattr(t.from_stage, 'value') else t.from_stage,
                "to_stage": t.to_stage.value if hasattr(t.to_stage, 'value') else t.to_stage,
                "occurred_at": t.occurred_at,
                "confidence": t.confidence
            }
            for t in transitions
        ]
        
        evidence_audit = [
            {
                "evidence_id": ev.evidence_id,
                "type": ev.evidence_type.value if hasattr(ev.evidence_type, 'value') else ev.evidence_type,
                "source_id": ev.source_id,
                "timestamp": ev.timestamp
            }
            for t in transitions for ev in t.evidence
        ]
        
        rules_fired = sum(d.rules_matched for d in diagnostics_list)
        rejected_candidates = sum(d.rejected_transition_count for d in diagnostics_list)
        
        confidence_factors_audit = [
            {
                "transition_id": t.transition_id,
                "factors": {
                    "intent_match": t.confidence_factors.intent_match,
                    "timeline_match": t.confidence_factors.timeline_match,
                    "conversation_match": t.confidence_factors.conversation_match,
                    "rule_strength": t.confidence_factors.rule_strength,
                    "evidence_count_factor": t.confidence_factors.evidence_count_factor,
                    "evidence_quality_factor": t.confidence_factors.evidence_quality_factor,
                    "source_consistency_factor": t.confidence_factors.source_consistency_factor,
                    "recency_factor": t.confidence_factors.recency_factor,
                }
            }
            for t in transitions if t.confidence_factors
        ]
        
        timestamps = {
            "journey_started_at": journey_state.journey_started_at,
            "stage_entered_at": journey_state.stage_entered_at,
            "last_transition_at": journey_state.last_transition_at,
            "events": [{"event_id": e.event_id, "timestamp": e.timestamp} for e in timeline.events]
        }
        
        provenance = {
            "workspace_id": journey_state.workspace_id,
            "entity_type": journey_state.entity_type,
            "entity_id": journey_state.entity_id,
            "journey_definition_id": journey_state.journey_definition_id
        }
        
        view: Dict[str, Any] = {
            "complete_transition_graph": complete_transition_graph,
            "evidence_audit": evidence_audit,
            "rules_fired": rules_fired,
            "confidence_factors_audit": confidence_factors_audit,
            "timestamps": timestamps,
            "provenance": provenance,
            "rejected_candidates": rejected_candidates
        }

        if maturity_result is not None:
            view["maturity_provenance"] = {
                "calculation_id": str(maturity_result.provenance.calculation_id),
                "engine_version": maturity_result.provenance.engine_version,
                "pipeline_version": maturity_result.provenance.pipeline_version,
                "configuration_version": maturity_result.provenance.configuration_version,
                "calculation_method": maturity_result.provenance.calculation_method,
            }
            view["maturity_diagnostics"] = {
                "total_execution_time_ms": maturity_result.diagnostics.total_execution_time_ms,
                "evidence_count": maturity_result.diagnostics.evidence_count,
                "transition_count": maturity_result.diagnostics.transition_count,
                "residency_count": maturity_result.diagnostics.residency_count,
                "probability_available": maturity_result.diagnostics.probability_available,
                "probability_sample_size": maturity_result.diagnostics.probability_sample_size,
            }

        return view
