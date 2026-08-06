"""
HunterOS Engage V1 - Relationship Models & Helpers
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class RelationshipMatchReport(BaseModel):
    """Execution diagnostics for relationship rule evaluations."""
    model_config = ConfigDict(frozen=True)

    rule_name: str
    rule_version: str
    relationships_generated: int
    matched: bool
    details: Dict[str, Any] = Field(default_factory=dict)
