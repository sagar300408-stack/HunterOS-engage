from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(frozen=True)
class RecommendationProvenance:
    provenance_id: UUID
    workspace_id: UUID
    source_modules: List[str]
    source_artifact_ids: List[UUID]
    generated_by: str
    generation_method: str
    pipeline_version: str
    engine_version: str
    schema_version: str
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
