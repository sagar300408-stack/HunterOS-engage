"""
HunterOS Engage V1 - Classification Stage 5: Compute Intent Relationships
"""

from __future__ import annotations

import time
from typing import List, Optional

from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import ClassifiedIntent
from app.domain.intents.classification.relationships.engine import (
    IntentRelationshipEngine,
    default_relationship_engine,
)


class ComputeIntentRelationshipsStage:
    """Stage 5: Generates structural, dependency, and conflict relationships."""

    def __init__(self, relationship_engine: Optional[IntentRelationshipEngine] = None):
        self._engine = relationship_engine or default_relationship_engine

    def execute(self, context: IntentClassificationContext) -> None:
        start = time.perf_counter()
        relationships = self._engine.compute_relationships(context)
        context.relationships = relationships

        # Attach relevant relationships to each ClassifiedIntent
        updated_intents: List[ClassifiedIntent] = []
        for ci in context.classified_intents:
            rel_for_intent = [
                r for r in relationships
                if r.source_intent_id == ci.classified_intent_id or r.target_intent_id == ci.classified_intent_id
            ]
            # Create updated immutable copy
            updated = ClassifiedIntent(
                classified_intent_id=ci.classified_intent_id,
                original_intent_id=ci.original_intent_id,
                canonical_intent_id=ci.canonical_intent_id,
                conversation_id=ci.conversation_id,
                workspace_id=ci.workspace_id,
                customer_id=ci.customer_id,
                business_category=ci.business_category,
                business_domain=ci.business_domain,
                business_process=ci.business_process,
                taxonomy_path=ci.taxonomy_path,
                taxonomy_paths=ci.taxonomy_paths,
                aliases=ci.aliases,
                confidence=ci.confidence,
                classification_method=ci.classification_method,
                supporting_evidence=ci.supporting_evidence,
                relationships=rel_for_intent,
                metadata=ci.metadata,
                classified_at=ci.classified_at,
            )
            updated_intents.append(updated)

        context.classified_intents = updated_intents
        elapsed = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage5_ComputeIntentRelationships", elapsed)
