"""
HunterOS Engage V1 — Journey Definition Registry & Utilities
Phase 2.4.1: Journey Foundation
"""

from __future__ import annotations

import uuid
from typing import Optional, Union

from app.domain.journey.definitions.core import (
    build_sales_journey_definition,
    build_service_journey_definition,
    build_support_journey_definition,
    register_core_definitions as _register_core,
)
from app.domain.journey.definitions.industry.real_estate import (
    build_real_estate_sales_journey,
    register_real_estate_definitions as _register_re,
)
from app.domain.journey.definitions.registry import (
    JourneyDefinitionRegistry,
    StageDefinitionRegistry,
    default_journey_registry,
    default_stage_registry,
)
from app.domain.journey.models import JourneyDefinition, JourneyType


def register_core_definitions(
    journey_registry: Optional[JourneyDefinitionRegistry] = None,
    stage_registry: Optional[StageDefinitionRegistry] = None,
) -> None:
    """Register all core cross-industry definitions in given or default registries."""
    j_reg = journey_registry or default_journey_registry
    s_reg = stage_registry or default_stage_registry
    _register_core(j_reg, s_reg)


def register_real_estate_definitions(
    journey_registry: Optional[JourneyDefinitionRegistry] = None,
    stage_registry: Optional[StageDefinitionRegistry] = None,
) -> None:
    """Register all real estate definitions in given or default registries."""
    j_reg = journey_registry or default_journey_registry
    s_reg = stage_registry or default_stage_registry
    _register_re(j_reg, s_reg)


def get_journey_definition(
    definition_id_or_type: Union[uuid.UUID, str, JourneyType],
    journey_registry: Optional[JourneyDefinitionRegistry] = None,
) -> Optional[JourneyDefinition]:
    """Look up a journey definition by UUID, string ID, or JourneyType."""
    j_reg = journey_registry or default_journey_registry
    if isinstance(definition_id_or_type, JourneyType):
        return j_reg.get_by_type(definition_id_or_type)
    if isinstance(definition_id_or_type, uuid.UUID):
        return j_reg.get(definition_id_or_type)
    # String can be UUID string or JourneyType name
    try:
        j_type = JourneyType(definition_id_or_type)
        res = j_reg.get_by_type(j_type)
        if res is not None:
            return res
    except (ValueError, KeyError):
        pass
    return j_reg.get(definition_id_or_type)


__all__ = [
    "StageDefinitionRegistry",
    "JourneyDefinitionRegistry",
    "default_stage_registry",
    "default_journey_registry",
    "build_sales_journey_definition",
    "build_service_journey_definition",
    "build_support_journey_definition",
    "build_real_estate_sales_journey",
    "register_core_definitions",
    "register_real_estate_definitions",
    "get_journey_definition",
]
