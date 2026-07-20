import uuid
from typing import List, Dict, Any

from app.domain.impact.models import ImpactEvent, ValueAttribution
from app.domain.impact.repository import ImpactRepository
from app.domain.impact.engines.evidence import EvidenceEngine
from app.domain.impact.engines.attribution import ValueAttributionEngine
from app.domain.impact.engines.roi import ROICalculator
from app.domain.impact.engines.confidence import ROIConfidenceEngine

class ImpactCollector:
    """
    The orchestrator that catches raw events, extracts evidence, 
    calculates ROI, assigns confidence, and persists ValueAttribution.
    """

    @classmethod
    async def process_event(cls, repo: ImpactRepository, event: ImpactEvent) -> ValueAttribution:
        # 1. Save raw event
        event = await repo.save_impact_event(event)
        
        # 2. Extract Evidence
        traces = EvidenceEngine.trace_evidence(event)
        
        # 3. Value Attribution (Categorization & Raw Metrics)
        category, raw_val, raw_name = ValueAttributionEngine.attribute(event)
        
        # 4. ROI Calculator
        config = await repo.get_financial_config(event.workspace_id)
        financial_value = ROICalculator.calculate_financial_value(category, raw_val, config)
        
        # 5. ROI Confidence
        confidence = ROIConfidenceEngine.evaluate(category, traces)
        
        # 6. Construct and Save Attribution
        attribution = ValueAttribution(
            event_id=event.id,
            workspace_id=event.workspace_id,
            category=category,
            raw_metric_name=raw_name,
            raw_metric_value=raw_val,
            estimated_financial_value=financial_value,
            confidence_score=confidence,
            currency="INR" # Could be pulled from config in real app
        )
        
        # Attach traces
        for trace in traces:
            attribution.evidence_traces.append(trace)
            
        await repo.save_attribution(attribution)
        
        return attribution
