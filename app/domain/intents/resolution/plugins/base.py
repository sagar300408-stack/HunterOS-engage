"""
HunterOS Engage V1 - Industry Resolution Plugin Base
Abstract base class for domain-specific multi-intent resolution plugins.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.intents.resolution.dominance.base import DominanceStrategy
from app.domain.intents.resolution.rules.base import ConflictRule, DependencyRule, RelationshipRule


class IndustryResolutionPlugin(ABC):
    """
    Plugin architecture for vertical industries.
    Bundles custom relationship rules, conflict rules, dependency rules, and dominance strategies.
    """

    def __init__(self, plugin_name: str, domain: str, version: str = "1.0.0") -> None:
        self.plugin_name: str = plugin_name
        self.domain: str = domain
        self.version: str = version

    @abstractmethod
    def get_relationship_rules(self) -> List[RelationshipRule]:
        """Return vertical-specific relationship rules."""
        return []

    @abstractmethod
    def get_conflict_rules(self) -> List[ConflictRule]:
        """Return vertical-specific conflict rules."""
        return []

    @abstractmethod
    def get_dependency_rules(self) -> List[DependencyRule]:
        """Return vertical-specific dependency rules."""
        return []

    @abstractmethod
    def get_dominance_strategies(self) -> List[DominanceStrategy]:
        """Return vertical-specific dominance strategies."""
        return []
