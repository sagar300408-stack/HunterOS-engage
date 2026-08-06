"""
HunterOS Engage V1 - Business Process Models
Dynamic process definitions decoupling workflow semantics from hardcoded enums.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domain.intents.classification.models import BusinessDomain


class BusinessProcessDefinition(BaseModel):
    """
    Metadata representation of a business process that an intent initiates or advances.
    """
    model_config = ConfigDict(frozen=True)

    process_id: str
    name: str
    description: str
    business_domain: BusinessDomain = BusinessDomain.CROSS_INDUSTRY
    sla_target_hours: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_id": self.process_id,
            "name": self.name,
            "description": self.description,
            "business_domain": self.business_domain.value,
            "sla_target_hours": self.sla_target_hours,
            "metadata": self.metadata,
        }
