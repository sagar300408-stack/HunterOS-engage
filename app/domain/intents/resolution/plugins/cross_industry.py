"""
HunterOS Engage V1 - Cross-Industry Resolution Plugin
Default baseline resolution rules and strategies for generic business contexts.
"""

from __future__ import annotations

from typing import List

from app.domain.intents.resolution.dominance.base import DominanceStrategy
from app.domain.intents.resolution.dominance.commercial import CommercialImportanceStrategy
from app.domain.intents.resolution.dominance.evidence_coverage import EvidenceCoverageStrategy
from app.domain.intents.resolution.dominance.frequency import FrequencyStrategy
from app.domain.intents.resolution.dominance.persistence import PersistenceStrategy
from app.domain.intents.resolution.plugins.base import IndustryResolutionPlugin
from app.domain.intents.resolution.rules.base import ConflictRule, DependencyRule, RelationshipRule
from app.domain.intents.resolution.rules.conflict_rules import (
    ContradictingIntentRule,
    DuplicateIntentRule,
    MutuallyExclusiveIntentRule,
    TimelineStateConflictRule,
)
from app.domain.intents.resolution.rules.dependency_rules import (
    BlockingSupportRule,
    PrerequisiteInquiryRule,
    SequentialRequirementRule,
)
from app.domain.intents.resolution.rules.relationship_rules import (
    ComplementaryCommercialRule,
    CrossIntentRelatedRule,
    SupportOperationalRule,
    TaxonomyHierarchyRelationshipRule,
)


class CrossIndustryResolutionPlugin(IndustryResolutionPlugin):
    """
    Standard plugin supplying baseline domain-agnostic rules and dominance strategies.
    """

    def __init__(self) -> None:
        super().__init__(
            plugin_name="CrossIndustryResolutionPlugin",
            domain="CROSS_INDUSTRY",
            version="1.0.0",
        )

    def get_relationship_rules(self) -> List[RelationshipRule]:
        return [
            TaxonomyHierarchyRelationshipRule(),
            ComplementaryCommercialRule(),
            SupportOperationalRule(),
            CrossIntentRelatedRule(),
        ]

    def get_conflict_rules(self) -> List[ConflictRule]:
        return [
            DuplicateIntentRule(),
            MutuallyExclusiveIntentRule(),
            ContradictingIntentRule(),
            TimelineStateConflictRule(),
        ]

    def get_dependency_rules(self) -> List[DependencyRule]:
        return [
            SequentialRequirementRule(),
            PrerequisiteInquiryRule(),
            BlockingSupportRule(),
        ]

    def get_dominance_strategies(self) -> List[DominanceStrategy]:
        return [
            EvidenceCoverageStrategy(weight=1.5),
            CommercialImportanceStrategy(weight=1.2),
            PersistenceStrategy(weight=1.0),
            FrequencyStrategy(weight=0.8),
        ]
