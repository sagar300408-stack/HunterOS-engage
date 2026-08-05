"""
HunterOS Engage — Context Composition Strategies (Phase 2.1.5)

Defines pluggable strategies determining which intelligence blocks should be loaded,
normalized, and composed for different domain perspectives.
"""

from __future__ import annotations

import abc
from typing import Dict, List, Optional, Union

from app.domain.memory.intelligence.models import ContextBlockType, ContextScope
from app.domain.memory.intelligence.schemas import ContextRequestOptions


class ContextCompositionStrategy(abc.ABC):
    """
    Abstract strategy governing block selection and composition rules.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def scope(self) -> ContextScope:
        raise NotImplementedError

    @abc.abstractmethod
    def determine_blocks(self, options: Optional[ContextRequestOptions] = None) -> List[ContextBlockType]:
        """Determine the set of ContextBlockType to load."""
        raise NotImplementedError


class Customer360CompositionStrategy(ContextCompositionStrategy):
    """Full 360-degree customer intelligence block composition."""

    @property
    def name(self) -> str:
        return "CUSTOMER_360"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.CUSTOMER

    def determine_blocks(self, options: Optional[ContextRequestOptions] = None) -> List[ContextBlockType]:
        if options and options.blocks:
            return [ContextBlockType(b.upper()) for b in options.blocks if b.upper() in ContextBlockType.__members__]

        blocks = [ContextBlockType.MEMORY, ContextBlockType.RELATIONSHIPS]
        if not options or options.include_timeline:
            blocks.append(ContextBlockType.TIMELINE)
        if options and options.include_versions:
            blocks.append(ContextBlockType.VERSIONS)
        if not options or options.include_projections:
            blocks.append(ContextBlockType.PROJECTIONS)
        if not options or options.include_statistics:
            blocks.append(ContextBlockType.STATISTICS)
        return blocks


class OrganizationCompositionStrategy(ContextCompositionStrategy):
    """B2B Organization & Company intelligence composition."""

    @property
    def name(self) -> str:
        return "ORGANIZATION"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.ORGANIZATION

    def determine_blocks(self, options: Optional[ContextRequestOptions] = None) -> List[ContextBlockType]:
        if options and options.blocks:
            return [ContextBlockType(b.upper()) for b in options.blocks if b.upper() in ContextBlockType.__members__]
        return [
            ContextBlockType.RELATIONSHIPS,
            ContextBlockType.PROJECTIONS,
            ContextBlockType.STATISTICS,
        ]


class OpportunityCompositionStrategy(ContextCompositionStrategy):
    """Deal & Opportunity network intelligence composition."""

    @property
    def name(self) -> str:
        return "OPPORTUNITY"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.OPPORTUNITY

    def determine_blocks(self, options: Optional[ContextRequestOptions] = None) -> List[ContextBlockType]:
        if options and options.blocks:
            return [ContextBlockType(b.upper()) for b in options.blocks if b.upper() in ContextBlockType.__members__]
        return [
            ContextBlockType.RELATIONSHIPS,
            ContextBlockType.PROJECTIONS,
            ContextBlockType.TIMELINE,
        ]


class PropertyCompositionStrategy(ContextCompositionStrategy):
    """Real estate Property asset intelligence composition."""

    @property
    def name(self) -> str:
        return "PROPERTY"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PROPERTY

    def determine_blocks(self, options: Optional[ContextRequestOptions] = None) -> List[ContextBlockType]:
        if options and options.blocks:
            return [ContextBlockType(b.upper()) for b in options.blocks if b.upper() in ContextBlockType.__members__]
        return [
            ContextBlockType.RELATIONSHIPS,
            ContextBlockType.PROJECTIONS,
            ContextBlockType.STATISTICS,
        ]


class ExecutiveCompositionStrategy(ContextCompositionStrategy):
    """Executive high-level workspace summary intelligence composition."""

    @property
    def name(self) -> str:
        return "EXECUTIVE"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.EXECUTIVE

    def determine_blocks(self, options: Optional[ContextRequestOptions] = None) -> List[ContextBlockType]:
        if options and options.blocks:
            return [ContextBlockType(b.upper()) for b in options.blocks if b.upper() in ContextBlockType.__members__]
        return [
            ContextBlockType.STATISTICS,
            ContextBlockType.PROJECTIONS,
        ]


class SelectiveCompositionStrategy(ContextCompositionStrategy):
    """Caller-specified arbitrary block selection."""

    @property
    def name(self) -> str:
        return "SELECTIVE"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.CUSTOM

    def determine_blocks(self, options: Optional[ContextRequestOptions] = None) -> List[ContextBlockType]:
        if options and options.blocks:
            return [ContextBlockType(b.upper()) for b in options.blocks if b.upper() in ContextBlockType.__members__]
        return [ContextBlockType.MEMORY, ContextBlockType.RELATIONSHIPS]


class CompositionStrategyRegistry:
    """Registry for discovering composition strategies."""

    def __init__(self) -> None:
        self._strategies: Dict[str, ContextCompositionStrategy] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(Customer360CompositionStrategy())
        self.register(OrganizationCompositionStrategy())
        self.register(OpportunityCompositionStrategy())
        self.register(PropertyCompositionStrategy())
        self.register(ExecutiveCompositionStrategy())
        self.register(SelectiveCompositionStrategy())

    def register(self, strategy: ContextCompositionStrategy) -> None:
        self._strategies[strategy.name.upper()] = strategy
        self._strategies[strategy.scope.value.upper()] = strategy

    def get_strategy(self, scope_or_name: Union[str, ContextScope]) -> ContextCompositionStrategy:
        key = scope_or_name.value.upper() if isinstance(scope_or_name, ContextScope) else str(scope_or_name).upper()
        return self._strategies.get(key, SelectiveCompositionStrategy())


default_strategy_registry = CompositionStrategyRegistry()
