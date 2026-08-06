"""
HunterOS Engage V1 - Intent Normalizer
Converts DetectedIntent entities into standardized CanonicalIntent representations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List
from app.domain.intents.classification.canonical.models import (
    CanonicalIntent,
    CanonicalPayload,
)
from app.domain.intents.models import DetectedIntent


class IntentNormalizer:
    """
    Normalizes any DetectedIntent instance into a standard CanonicalIntent entity.
    """

    def normalize(self, intent: Any) -> CanonicalIntent:
        """Transforms a DetectedIntent or duck-typed intent object into CanonicalIntent."""
        ev = getattr(intent, "supporting_evidence", None)
        
        # Determine intent_type / canonical_name
        intent_type = getattr(intent, "intent_type", None) or getattr(intent, "name", "UNKNOWN")
        raw_type = intent_type.value if hasattr(intent_type, "value") else str(intent_type)

        # Determine category
        cat = getattr(intent, "category", None) or getattr(intent, "taxonomy_category", None)
        raw_cat = cat.value if hasattr(cat, "value") else (str(cat) if cat else None)

        # Determine importance
        imp = getattr(intent, "importance", None) or getattr(intent, "business_importance", None)
        raw_imp = imp.value if hasattr(imp, "value") else (str(imp) if imp else None)

        # Determine detection method
        det_method = getattr(intent, "detection_method", "RULE_BASED")
        raw_det_method = det_method.value if hasattr(det_method, "value") else str(det_method)

        metadata = dict(getattr(intent, "metadata", {}))
        provenance = getattr(intent, "provenance", {})
        prov_dict = provenance.model_dump() if hasattr(provenance, "model_dump") else (
            provenance.to_dict() if hasattr(provenance, "to_dict") else dict(provenance)
        )

        payload = CanonicalPayload(
            intent_type_raw=raw_type,
            category_raw=raw_cat,
            importance_raw=raw_imp,
            primary_entities=dict(metadata.get("entities", {})),
            parameters=dict(metadata.get("parameters", {})),
            provenance_details=prov_dict,
        )

        original_id = getattr(intent, "intent_id", None) or getattr(intent, "id", None)
        import uuid
        if original_id is None:
            original_id = uuid.uuid4()

        title = getattr(intent, "title", "")
        desc = getattr(intent, "description", "")

        return CanonicalIntent(
            original_intent_id=original_id,
            conversation_id=getattr(intent, "conversation_id", "default_conv"),
            workspace_id=getattr(intent, "workspace_id", None),
            customer_id=getattr(intent, "customer_id", None),
            canonical_name=raw_type.lower(),
            normalized_title=title.strip().lower() if title else "",
            normalized_description=desc.strip().lower() if desc else "",
            confidence=max(0.0, min(1.0, float(getattr(intent, "confidence", 1.0)))),
            payload=payload,
            source_detection_method=raw_det_method,
            evidence_message_ids=list(getattr(ev, "source_message_ids", [])) if ev else [],
            evidence_event_ids=list(getattr(ev, "source_event_ids", [])) if ev else [],
            evidence_fact_ids=list(getattr(ev, "source_fact_ids", [])) if ev else [],
            evidence_milestone_ids=list(getattr(ev, "source_milestone_ids", [])) if ev else [],
            evidence_moment_ids=list(getattr(ev, "source_moment_ids", [])) if ev else [],
            evidence_insight_ids=list(getattr(ev, "source_insight_ids", [])) if ev else [],
            text_snippets=list(getattr(ev, "text_snippets", [])) if ev else [],
            metadata=metadata,
            created_at=getattr(intent, "detected_at", None) or datetime.now(timezone.utc),
        )

    def normalize_all(self, intents: List[DetectedIntent]) -> List[CanonicalIntent]:
        """Transforms a collection of DetectedIntents into CanonicalIntents."""
        return [self.normalize(i) for i in intents]


default_intent_normalizer = IntentNormalizer()
