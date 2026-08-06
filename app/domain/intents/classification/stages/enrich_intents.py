"""
HunterOS Engage V1 - Classification Stage 4: Enrich Intents
Attaches taxonomy paths, business processes, and existing metadata (zero inference).
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional
import uuid

from app.domain.intents.classification.canonical.models import CanonicalIntent
from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import (
    ClassifiedIntent,
    ClassificationMethod,
)
from app.domain.intents.classification.models import IntentEvidence
from app.domain.intents.classification.process.registry import (
    BusinessProcessRegistry,
    default_business_process_registry,
)
from app.domain.intents.classification.rules.base import ClassificationCandidate
from app.domain.intents.classification.taxonomy.graph import (
    BusinessIntentTaxonomyGraph,
    default_taxonomy_graph,
)


class EnrichIntentsStage:
    """Stage 4: Metadata enrichment without predictive inference."""

    def __init__(
        self,
        taxonomy_graph: Optional[BusinessIntentTaxonomyGraph] = None,
        process_registry: Optional[BusinessProcessRegistry] = None,
    ):
        self._taxonomy_graph = taxonomy_graph or default_taxonomy_graph
        self._process_registry = process_registry or default_business_process_registry

    def execute(
        self,
        context: IntentClassificationContext,
        candidates: Dict[uuid.UUID, ClassificationCandidate],
    ) -> None:
        start = time.perf_counter()
        classified_intents: List[ClassifiedIntent] = []

        for canonical in context.canonical_intents:
            candidate = candidates.get(canonical.canonical_intent_id)
            if not candidate:
                continue

            # 1. Resolve Taxonomy Paths from Graph
            primary_path = self._taxonomy_graph.find_primary_path(candidate.taxonomy_node_id)
            all_paths = [
                p.path_str for p in self._taxonomy_graph.get_all_paths_to_root(candidate.taxonomy_node_id)
            ]
            if not all_paths:
                all_paths = [primary_path]

            # 2. Resolve Business Process Definition
            proc_def = self._process_registry.get(candidate.process)
            proc_name = proc_def.process_id if proc_def else candidate.process

            # 3. Compute bounded confidence
            final_conf = min(1.0, max(0.0, canonical.confidence + candidate.confidence_boost))

            # 4. Construct Supporting Evidence DTO
            evidence = IntentEvidence(
                source_message_ids=list(canonical.evidence_message_ids),
                source_event_ids=list(canonical.evidence_event_ids),
                source_fact_ids=list(canonical.evidence_fact_ids),
                source_milestone_ids=list(canonical.evidence_milestone_ids),
                source_moment_ids=list(canonical.evidence_moment_ids),
                source_insight_ids=list(canonical.evidence_insight_ids),
                text_snippets=list(canonical.text_snippets),
                confidence_score=final_conf,
                metadata={"confidence_rationale": f"Classified into '{primary_path}' via rule-based candidate match."},
            )

            # 5. Build Enriched ClassifiedIntent
            enriched = ClassifiedIntent(
                original_intent_id=canonical.original_intent_id,
                canonical_intent_id=canonical.canonical_intent_id,
                conversation_id=canonical.conversation_id,
                workspace_id=canonical.workspace_id,
                customer_id=canonical.customer_id,
                business_category=candidate.category,
                business_domain=candidate.domain,
                business_process=proc_name,
                taxonomy_path=primary_path,
                taxonomy_paths=all_paths,
                aliases=list(set(candidate.aliases + [canonical.canonical_name])),
                confidence=round(final_conf, 4),
                classification_method=ClassificationMethod.TAXONOMY_GRAPH_MAPPING,
                supporting_evidence=evidence,
                relationships=[],
                metadata={
                    **canonical.metadata,
                    **candidate.metadata,
                    "taxonomy_node_id": candidate.taxonomy_node_id,
                    "normalized_title": canonical.normalized_title,
                    "normalized_description": canonical.normalized_description,
                },
                classified_at=canonical.created_at,
            )
            classified_intents.append(enriched)

        context.classified_intents = classified_intents
        elapsed = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage4_EnrichIntents", elapsed)
