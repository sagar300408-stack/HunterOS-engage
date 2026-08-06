"""
HunterOS Engage V1 - Classification Stage 3: Classify Intents
Executes deterministic classification rules across canonical intents.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional
import uuid

from app.domain.intents.classification.canonical.models import CanonicalIntent
from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import (
    BusinessDomain,
    ClassificationMethod,
    IntentCategory,
)
from app.domain.intents.classification.rules.base import ClassificationCandidate
from app.domain.intents.classification.rules.registry import (
    ClassificationRuleRegistry,
    default_classification_rule_registry,
)


class ClassifyIntentsStage:
    """Stage 3: Applies classification rule packs to produce candidates."""

    def __init__(self, rule_registry: Optional[ClassificationRuleRegistry] = None):
        self._rule_registry = rule_registry or default_classification_rule_registry

    def execute(self, context: IntentClassificationContext) -> Dict[uuid.UUID, ClassificationCandidate]:
        start = time.perf_counter()
        rules = self._rule_registry.list_all_rules(
            active_pack_names=context.active_plugins if context.active_plugins else None
        )
        context.applied_rule_packs = [p.pack_name for p in self._rule_registry.list_packs()]

        candidates: Dict[uuid.UUID, ClassificationCandidate] = {}

        for canonical in context.canonical_intents:
            matched_candidate: Optional[ClassificationCandidate] = None

            for rule in rules:
                context.executed_rules.append(rule.rule_name)
                try:
                    cand = rule.evaluate(canonical, context)
                    if cand:
                        context.matched_rules.append(rule.rule_name)
                        matched_candidate = cand
                        break
                    else:
                        context.rejected_rules.append(rule.rule_name)
                except Exception as e:
                    context.add_warning(f"Rule evaluation error in '{rule.rule_name}': {str(e)}")

            # Fallback candidate if no specific rule matched
            if not matched_candidate:
                matched_candidate = self._fallback_classification(canonical)

            candidates[canonical.canonical_intent_id] = matched_candidate

        elapsed = (time.perf_counter() - start) * 1000.0
        context.record_stage_timing("Stage3_ClassifyIntents", elapsed)
        return candidates

    def _fallback_classification(self, canonical: CanonicalIntent) -> ClassificationCandidate:
        """Determines a safe default classification based on canonical raw fields."""
        raw_cat = (canonical.payload.category_raw or "").upper()
        if "COMMERCIAL" in raw_cat:
            cat = IntentCategory.COMMERCIAL
            node = "commercial"
            proc = "SALES_QUALIFICATION"
        elif "OPERATIONAL" in raw_cat:
            cat = IntentCategory.OPERATIONAL
            node = "operational"
            proc = "APPOINTMENT_SCHEDULING"
        elif "RELATIONSHIP" in raw_cat:
            cat = IntentCategory.RELATIONSHIP
            node = "relationship"
            proc = "RETENTION_RELATIONSHIP"
        elif "INFORMATION" in raw_cat:
            cat = IntentCategory.INFORMATION
            node = "information"
            proc = "GENERAL_DISCOVERY"
        else:
            cat = IntentCategory.INFORMATION
            node = "information.general_inquiry"
            proc = "GENERAL_DISCOVERY"

        return ClassificationCandidate(
            category=cat,
            domain=BusinessDomain.CROSS_INDUSTRY,
            process=proc,
            taxonomy_node_id=node,
            confidence_boost=0.0,
            aliases=[canonical.canonical_name],
        )
