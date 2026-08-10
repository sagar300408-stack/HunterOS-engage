from __future__ import annotations

import dataclasses
from typing import Any, List, Optional
from app.domain.journey.integration.models import JourneyIntelligenceContext

class JourneyContextBuilder:
    """Builder for assembling a JourneyIntelligenceContext."""
    
    def __init__(self, workspace_uri: str, tenant_id: str, journey_id: str):
        self._workspace_uri = workspace_uri
        self._tenant_id = tenant_id
        self._journey_id = journey_id
        self._blocks: List[Any] = []
        self._metadata: dict = {}

    def load_artifacts(self, artifacts: List[Any]) -> JourneyContextBuilder:
        # Logic to load requested artifacts
        return self

    def assemble_blocks(self, blocks: List[Any]) -> JourneyContextBuilder:
        self._blocks.extend(blocks)
        return self

    def preserve_provenance(self, provenance_data: Any) -> JourneyContextBuilder:
        self._metadata["provenance"] = provenance_data
        return self

    def calculate_completeness(self) -> float:
        if not self._blocks:
            return 0.0
        return 1.0

    def build(self) -> JourneyIntelligenceContext:
        """Builds the final immutable JourneyIntelligenceContext."""
        return JourneyIntelligenceContext(
            workspace_uri=self._workspace_uri,
            tenant_id=self._tenant_id,
            journey_id=self._journey_id,
            blocks=tuple(self._blocks),
            metadata=self._metadata
        )
