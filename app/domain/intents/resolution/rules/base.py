"""
HunterOS Engage V1 - Resolution Rules Base
Abstract base classes for relationship, conflict, and dependency detection rules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import (
    IntentConflict,
    IntentDependency,
    IntentNode,
    IntentRelationship,
    IntentResolutionGraph,
)


class ResolutionRule(ABC):
    """Base class for all deterministic resolution rules."""

    def __init__(self, rule_name: str, domain: str = "CROSS_INDUSTRY", priority: int = 100) -> None:
        self.rule_name: str = rule_name
        self.domain: str = domain
        self.priority: int = priority


class RelationshipRule(ResolutionRule):
    """Rule for detecting descriptive relationship edges between intent pairs."""

    @abstractmethod
    def evaluate_relationships(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentRelationship]:
        """Detect and return relationship edges between nodes."""
        pass


class ConflictRule(ResolutionRule):
    """Rule for detecting factual conflicts, contradictions, or competing intents."""

    @abstractmethod
    def evaluate_conflicts(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentConflict]:
        """Detect and return conflicts among intent nodes."""
        pass


class DependencyRule(ResolutionRule):
    """Rule for detecting observed business dependencies between intents."""

    @abstractmethod
    def evaluate_dependencies(
        self,
        nodes: List[IntentNode],
        graph: IntentResolutionGraph,
        context: MultiIntentResolutionContext,
    ) -> List[IntentDependency]:
        """Detect and return dependencies between intent nodes."""
        pass
