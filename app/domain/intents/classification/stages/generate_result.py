"""
HunterOS Engage V1 - Classification Stage 8: Generate Classification Result
Constructs immutable IntentClassificationResult aggregate root with complete metadata and provenance.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import time
from typing import Counter as CounterType, Dict, Optional
import uuid

from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import (
    BusinessDomain,
    ClassificationDiagnostics,
    ClassificationMetadata,
    ClassificationProvenance,
    IntentCategory,
    IntentClassificationResult,
)


class GenerateClassificationResultStage:
    """Stage 8: Finalizes metadata and builds the aggregate root entity."""

    def execute(self, context: IntentClassificationContext) -> IntentClassificationResult:
        start = time.perf_counter()

        # 1. Compute Category & Domain Distributions
        cat_counts: CounterType[str] = Counter(i.business_category.value for i in context.classified_intents)
        dom_counts: CounterType[str] = Counter(i.business_domain.value for i in context.classified_intents)
        grp_counts: CounterType[str] = Counter(g.group_type.value for g in context.groups)

        primary_cat: Optional[IntentCategory] = None
        if cat_counts:
            most_common_cat = cat_counts.most_common(1)[0][0]
            primary_cat = IntentCategory(most_common_cat)

        primary_dom: Optional[BusinessDomain] = None
        if dom_counts:
            most_common_dom = dom_counts.most_common(1)[0][0]
            primary_dom = BusinessDomain(most_common_dom)

        primary_proc: Optional[str] = None
        proc_counts = Counter(i.business_process for i in context.classified_intents)
        if proc_counts:
            primary_proc = proc_counts.most_common(1)[0][0]

        total_duration = sum(context.stage_timings.values())

        # 2. Build Metadata
        metadata = ClassificationMetadata(
            conversation_id=context.conversation_id,
            workspace_id=context.workspace_id,
            customer_id=context.customer_id,
            classification_version="2.3.2",
            taxonomy_version="2.3.2",
            total_detected_intents=len(context.loaded_intents),
            total_classified_intents=len(context.classified_intents),
            total_relationships=len(context.relationships),
            total_groups=len(context.groups),
            primary_category=primary_cat,
            primary_domain=primary_dom,
            primary_process=primary_proc,
            category_distribution=dict(cat_counts),
            domain_distribution=dict(dom_counts),
            group_distribution=dict(grp_counts),
            execution_duration_ms=round(total_duration, 3),
        )

        # 3. Build Diagnostics
        diagnostics = ClassificationDiagnostics(
            is_valid=(len(context.validation_errors) == 0),
            applied_plugins=context.applied_plugins,
            applied_rule_packs=context.applied_rule_packs,
            executed_rules=list(set(context.executed_rules)),
            matched_rules=list(set(context.matched_rules)),
            rejected_rules=list(set(context.rejected_rules)),
            validation_warnings=context.validation_warnings,
            validation_errors=context.validation_errors,
            stage_timings_ms=context.stage_timings,
        )

        # 4. Build Provenance
        event_cnt = len(context.get_events())
        fact_cnt = len(context.get_facts())
        insight_cnt = len(context.get_actions()) + len(context.get_risks()) + len(context.get_opportunities())

        provenance = ClassificationProvenance(
            classification_version="2.3.2",
            taxonomy_version="2.3.2",
            detection_result_id=context.detection_result.detection_id if context.detection_result else None,
            rule_packs=context.applied_rule_packs,
            plugin_versions={p: "1.0.0" for p in context.applied_plugins},
            source_event_count=event_cnt,
            source_fact_count=fact_cnt,
            source_insight_count=insight_cnt,
            classified_by="IntentClassificationEngine_v2.3.2",
            generated_at=datetime.now(timezone.utc),
        )

        elapsed = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage8_GenerateClassificationResult", elapsed)

        return IntentClassificationResult(
            conversation_id=context.conversation_id,
            workspace_id=context.workspace_id,
            customer_id=context.customer_id,
            classified_intents=context.classified_intents,
            relationships=context.relationships,
            groups=context.groups,
            metadata=metadata,
            diagnostics=diagnostics,
            provenance=provenance,
        )
