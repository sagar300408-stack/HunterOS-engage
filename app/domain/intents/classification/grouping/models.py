"""
HunterOS Engage V1 - Grouping Models & Diagnostics
"""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class GroupAggregationReport(BaseModel):
    """Diagnostics for grouping stage."""
    model_config = ConfigDict(frozen=True)

    total_groups_formed: int
    group_types: List[str]
    group_details: Dict[str, Any] = Field(default_factory=dict)
