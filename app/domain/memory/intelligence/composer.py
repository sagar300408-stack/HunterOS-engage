"""
HunterOS Engage — Context Composer (Phase 2.1.5)

Deterministic assembler that compiles normalized memory, knowledge graph, timeline,
and projection blocks into a unified ComposedContext with full provenance lineage.
Strictly performs composition only — zero AI reasoning or inference.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.memory.intelligence.models import (
    ComposedContext,
    ContextBlock,
    ContextBlockType,
    ContextCompletenessReport,
    ContextLineage,
    ContextMetadata,
    ContextScope,
)
from app.domain.memory.intelligence.registry import ContextDescriptor
from app.domain.memory.intelligence.validation import (
    ContextValidator,
    default_context_validator,
)


class ContextComposer:
    """
    Composes normalized blocks into a structured ComposedContext.
    """

    def __init__(
        self,
        validator: Optional[ContextValidator] = None,
    ) -> None:
        self._validator = validator or default_context_validator

    def compose(
        self,
        scope: ContextScope,
        entity_id: Optional[str],
        workspace_id: Optional[uuid.UUID],
        descriptor: Optional[ContextDescriptor],
        requested_blocks: List[ContextBlockType],
        loaded_blocks: Dict[ContextBlockType, Any],
        projections_applied: Optional[List[str]] = None,
        errors: Optional[Dict[ContextBlockType, str]] = None,
        start_time: Optional[float] = None,
    ) -> ComposedContext:
        """
        Assemble the final ComposedContext with metadata, completeness report, and lineage.
        """
        now = datetime.now(timezone.utc)
        exec_ms = round((time.time() - start_time) * 1000, 2) if start_time else 0.0

        # 1. Build Lineage
        mem_ids: List[str] = []
        rel_ids: List[str] = []
        tl_ids: List[str] = []

        # Extract memory IDs
        mem_data = loaded_blocks.get(ContextBlockType.MEMORY)
        if isinstance(mem_data, dict):
            if "id" in mem_data:
                mem_ids.append(str(mem_data["id"]))
            if "customer_id" in mem_data and str(mem_data["customer_id"]) not in mem_ids:
                mem_ids.append(str(mem_data["customer_id"]))
        elif isinstance(mem_data, list):
            for m in mem_data:
                if isinstance(m, dict) and "id" in m:
                    mem_ids.append(str(m["id"]))

        # Extract relationship IDs
        rel_data = loaded_blocks.get(ContextBlockType.RELATIONSHIPS)
        if isinstance(rel_data, list):
            for r in rel_data:
                if isinstance(r, dict) and "id" in r:
                    rel_ids.append(str(r["id"]))

        # Extract timeline event IDs
        tl_data = loaded_blocks.get(ContextBlockType.TIMELINE)
        if isinstance(tl_data, list):
            for e in tl_data:
                if isinstance(e, dict) and "id" in e:
                    tl_ids.append(str(e["id"]))

        lineage = ContextLineage(
            source_memory_ids=mem_ids,
            source_relationship_ids=rel_ids,
            source_timeline_event_ids=tl_ids,
            projections_applied=projections_applied or [],
            generated_at=now,
            source_modules=["memory_foundation", "knowledge_graph", "timeline_audit"],
            details={
                "block_counts": {b.value: len(v) if isinstance(v, (list, dict)) else 1 for b, v in loaded_blocks.items()}
            },
        )

        # 2. Evaluate Completeness
        completeness = self._validator.evaluate_completeness(
            descriptor=descriptor,
            requested_blocks=requested_blocks,
            loaded_blocks=loaded_blocks,
            errors=errors,
        )

        # 3. Build Metadata
        metadata = ContextMetadata(
            context_id=uuid.uuid4(),
            context_version=1,
            generated_at=now,
            schema_version=descriptor.schema_version if descriptor else "1.0.0",
            source_modules=["memory_foundation", "knowledge_graph"],
            execution_time_ms=exec_ms,
            workspace_id=workspace_id,
        )

        # 4. Build Context Blocks
        composed_blocks: Dict[ContextBlockType, ContextBlock] = {}
        for b_type in requested_blocks:
            data = loaded_blocks.get(b_type, {})
            err = (errors or {}).get(b_type)
            composed_blocks[b_type] = ContextBlock(
                block_type=b_type,
                data=data if isinstance(data, dict) else {"items": data} if isinstance(data, list) else {"value": data},
                loaded=data is not None and not err,
                error=err,
            )

        return ComposedContext(
            scope=scope,
            entity_id=entity_id,
            workspace_id=workspace_id,
            metadata=metadata,
            lineage=lineage,
            completeness=completeness,
            blocks=composed_blocks,
        )
