from typing import List, Dict, Any
from app.domain.impact.models import ImpactEvent, EvidenceTrace

class EvidenceEngine:
    """
    Builds the evidentiary chain justifying the impact of an event.
    """

    @classmethod
    def trace_evidence(cls, event: ImpactEvent) -> List[EvidenceTrace]:
        """
        Extracts the causal chain of events from the payload.
        """
        traces = []
        payload = event.payload
        
        # In a real system, this might query an event lineage database.
        # For this milestone, we extract it from the payload if provided.
        sequence = payload.get("evidence_chain", [])
        
        for idx, evidence_text in enumerate(sequence):
            trace = EvidenceTrace(
                sequence_order=idx + 1,
                evidence_text=evidence_text
            )
            traces.append(trace)
            
        if not traces:
            # Fallback evidence
            traces.append(EvidenceTrace(sequence_order=1, evidence_text=f"Direct observation of {event.event_type}"))
            
        return traces
