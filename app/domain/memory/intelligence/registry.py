"""
HunterOS Engage — Context Schema Registry (Phase 2.1.5)

Manages registration, discovery, and resolution of context schemas and descriptors.
Allows future modules to dynamically plug in new context schemas without modifying core code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from app.domain.memory.intelligence.models import ContextBlockType, ContextScope


@dataclass(frozen=True)
class ContextDescriptor:
    """
    Metadata descriptor defining the composition rules and requirements for a context schema.
    """
    name: str
    scope: ContextScope
    default_blocks: List[ContextBlockType]
    required_blocks: List[ContextBlockType] = field(default_factory=list)
    description: str = ""
    schema_version: str = "1.0.0"
    is_custom: bool = False

    def to_dict(self) -> Dict[str, Union[str, bool, List[str]]]:
        return {
            "name": self.name,
            "scope": self.scope.value,
            "default_blocks": [b.value for b in self.default_blocks],
            "required_blocks": [b.value for b in self.required_blocks],
            "description": self.description,
            "schema_version": self.schema_version,
            "is_custom": self.is_custom,
        }


class ContextSchemaRegistry:
    """
    Dynamic registry for context schemas and descriptors.
    """

    def __init__(self) -> None:
        self._descriptors: Dict[str, ContextDescriptor] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register HunterOS built-in core context schemas."""
        # 1. Customer Context
        self.register(
            ContextDescriptor(
                name="CUSTOMER",
                scope=ContextScope.CUSTOMER,
                default_blocks=[
                    ContextBlockType.MEMORY,
                    ContextBlockType.RELATIONSHIPS,
                    ContextBlockType.TIMELINE,
                    ContextBlockType.VERSIONS,
                    ContextBlockType.PROJECTIONS,
                    ContextBlockType.STATISTICS,
                ],
                required_blocks=[ContextBlockType.MEMORY],
                description="Comprehensive 360-degree customer intelligence context.",
                schema_version="1.0.0",
            )
        )

        # 2. Organization Context
        self.register(
            ContextDescriptor(
                name="ORGANIZATION",
                scope=ContextScope.ORGANIZATION,
                default_blocks=[
                    ContextBlockType.RELATIONSHIPS,
                    ContextBlockType.PROJECTIONS,
                    ContextBlockType.STATISTICS,
                ],
                required_blocks=[ContextBlockType.RELATIONSHIPS],
                description="B2B Company & Organization hierarchy and relationship network context.",
                schema_version="1.0.0",
            )
        )

        # 3. Opportunity Context
        self.register(
            ContextDescriptor(
                name="OPPORTUNITY",
                scope=ContextScope.OPPORTUNITY,
                default_blocks=[
                    ContextBlockType.RELATIONSHIPS,
                    ContextBlockType.PROJECTIONS,
                    ContextBlockType.TIMELINE,
                ],
                required_blocks=[ContextBlockType.RELATIONSHIPS],
                description="Commercial deal and opportunity network context with linked stakeholders and properties.",
                schema_version="1.0.0",
            )
        )

        # 4. Property Context
        self.register(
            ContextDescriptor(
                name="PROPERTY",
                scope=ContextScope.PROPERTY,
                default_blocks=[
                    ContextBlockType.RELATIONSHIPS,
                    ContextBlockType.PROJECTIONS,
                    ContextBlockType.STATISTICS,
                ],
                required_blocks=[ContextBlockType.RELATIONSHIPS],
                description="Real estate asset network context linking owners, managers, and interested prospects.",
                schema_version="1.0.0",
            )
        )

        # 5. Executive Context
        self.register(
            ContextDescriptor(
                name="EXECUTIVE",
                scope=ContextScope.EXECUTIVE,
                default_blocks=[
                    ContextBlockType.STATISTICS,
                    ContextBlockType.PROJECTIONS,
                ],
                required_blocks=[ContextBlockType.STATISTICS],
                description="Executive-level high-altitude workspace topology and memory statistics context.",
                schema_version="1.0.0",
            )
        )

        # 6. Custom Context
        self.register(
            ContextDescriptor(
                name="CUSTOM",
                scope=ContextScope.CUSTOM,
                default_blocks=[
                    ContextBlockType.MEMORY,
                    ContextBlockType.RELATIONSHIPS,
                ],
                required_blocks=[],
                description="Flexible schema-free custom composed context.",
                schema_version="1.0.0",
                is_custom=True,
            )
        )

    def register(self, descriptor: ContextDescriptor) -> None:
        """Register a new or updated context schema descriptor."""
        key = descriptor.name.upper()
        self._descriptors[key] = descriptor
        if descriptor.scope:
            self._descriptors[descriptor.scope.value.upper()] = descriptor

    def get(self, name_or_scope: Union[str, ContextScope]) -> Optional[ContextDescriptor]:
        """Resolve a descriptor by name or ContextScope."""
        key = name_or_scope.value.upper() if isinstance(name_or_scope, ContextScope) else str(name_or_scope).upper()
        return self._descriptors.get(key)

    def is_registered(self, name_or_scope: Union[str, ContextScope]) -> bool:
        """Check if a schema descriptor exists."""
        return self.get(name_or_scope) is not None

    def list_descriptors(self) -> List[ContextDescriptor]:
        """List all unique registered schema descriptors."""
        seen = set()
        unique = []
        for d in self._descriptors.values():
            if d.name not in seen:
                seen.add(d.name)
                unique.append(d)
        return unique


# Default singleton instance
default_context_schema_registry = ContextSchemaRegistry()
