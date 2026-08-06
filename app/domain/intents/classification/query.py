"""
HunterOS Engage V1 - Intent Classification Query Engine
CQRS read model and descriptive analytics queries.
"""

from __future__ import annotations

from collections import Counter
from typing import Counter as CounterType, Dict, List, Optional
import uuid

from app.domain.intents.classification.models import (
    BusinessDomain,
    ClassifiedIntent,
    IntentCategory,
    IntentClassificationResult,
)
from app.domain.intents.classification.repository import (
    InMemoryIntentClassificationRepository,
    default_classification_repository,
)
from app.domain.intents.classification.schemas import IntentAnalyticsQueryDTO


class IntentClassificationQueryEngine:
    """
    Handles CQRS read queries and descriptive analytics aggregations.
    """

    def __init__(self, repository: Optional[InMemoryIntentClassificationRepository] = None):
        self._repository = repository or default_classification_repository

    def query_intents(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[str] = None,
        category: Optional[IntentCategory] = None,
        domain: Optional[BusinessDomain] = None,
        process: Optional[str] = None,
        taxonomy_path_contains: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> List[ClassifiedIntent]:
        """Query individual classified intents matching filter criteria."""
        results: List[IntentClassificationResult]
        if workspace_id:
            results = self._repository.list_by_workspace(workspace_id)
        elif conversation_id:
            results = self._repository.get_by_conversation_id(conversation_id)
        else:
            results = self._repository.list_all()

        matched: List[ClassifiedIntent] = []
        for r in results:
            for ci in r.classified_intents:
                if category and ci.business_category != category:
                    continue
                if domain and ci.business_domain != domain:
                    continue
                if process and ci.business_process != process:
                    continue
                if taxonomy_path_contains and taxonomy_path_contains.lower() not in ci.taxonomy_path.lower():
                    continue
                if ci.confidence < min_confidence:
                    continue
                matched.append(ci)

        return matched

    def run_analytics_query(self, workspace_id: Optional[uuid.UUID] = None) -> IntentAnalyticsQueryDTO:
        """
        Calculates descriptive summary analytics across stored classifications.
        """
        results: List[IntentClassificationResult] = (
            self._repository.list_by_workspace(workspace_id)
            if workspace_id
            else self._repository.list_all()
        )

        total_classifications = len(results)
        all_intents: List[ClassifiedIntent] = [ci for r in results for ci in r.classified_intents]
        total_classified = len(all_intents)

        cat_counter: CounterType[str] = Counter(i.business_category.value for i in all_intents)
        dom_counter: CounterType[str] = Counter(i.business_domain.value for i in all_intents)
        proc_counter: CounterType[str] = Counter(i.business_process for i in all_intents)

        all_rels = [rel for r in results for rel in r.relationships]
        rel_counter: CounterType[str] = Counter(rel.relationship_type.value for rel in all_rels)

        all_grps = [grp for r in results for grp in r.groups]
        grp_counter: CounterType[str] = Counter(grp.group_type.value for grp in all_grps)

        # Total detected across metadata
        total_detected = sum(r.metadata.total_detected_intents for r in results)
        coverage_rate = round(total_classified / max(1, total_detected), 4)

        avg_conf = (
            round(sum(i.confidence for i in all_intents) / max(1, total_classified), 4)
            if total_classified > 0
            else 1.0
        )

        rule_counter: CounterType[str] = Counter(
            rule for r in results for rule in r.diagnostics.matched_rules
        )

        return IntentAnalyticsQueryDTO(
            workspace_id=workspace_id,
            total_classifications=total_classifications,
            total_classified_intents=total_classified,
            category_distribution=dict(cat_counter),
            domain_distribution=dict(dom_counter),
            process_distribution=dict(proc_counter),
            relationship_distribution=dict(rel_counter),
            group_distribution=dict(grp_counter),
            coverage_rate=coverage_rate,
            average_confidence=avg_conf,
            rule_usage_counts=dict(rule_counter),
        )


default_classification_query_engine = IntentClassificationQueryEngine()
