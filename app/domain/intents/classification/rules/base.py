"""
HunterOS Engage V1 - Classification Rule Base Classes
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.intents.classification.canonical.models import CanonicalIntent
from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
)

if TYPE_CHECKING:
    from app.domain.intents.classification.context import IntentClassificationContext


class ClassificationCandidate(BaseModel):
    """Candidate output produced by a classification rule match."""
    model_config = ConfigDict(frozen=True)

    category: IntentCategory
    domain: BusinessDomain = BusinessDomain.CROSS_INDUSTRY
    process: str = "GENERAL_DISCOVERY"
    taxonomy_node_id: str
    confidence_boost: float = 0.0
    aliases: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AbstractClassificationRule(ABC):
    """Abstract base class for a single deterministic intent classification rule."""

    def __init__(self, rule_name: str, rule_version: str = "1.0.0", description: str = ""):
        self.rule_name = rule_name
        self.rule_version = rule_version
        self.description = description

    @abstractmethod
    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        """Evaluate if this rule applies to the canonical intent."""
        pass


class AbstractClassificationRulePack(ABC):
    """Abstract collection of related classification rules."""

    def __init__(self, pack_name: str, version: str = "1.0.0", description: str = ""):
        self.pack_name = pack_name
        self.version = version
        self.description = description

    @abstractmethod
    def get_rules(self) -> List[AbstractClassificationRule]:
        """Return the list of rules in this pack."""
        pass
