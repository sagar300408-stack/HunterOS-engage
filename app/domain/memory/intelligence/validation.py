"""
HunterOS Engage — Context Validation Framework (Phase 2.1.5)

Provides deterministic validation for composed contexts including:
- Missing data detection
- Invalid reference checking
- Cross-workspace tenant security checks
- Completeness & diagnostic quality scoring
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.domain.memory.intelligence.models import (
    ContextBlockType,
    ContextCompletenessReport,
    ContextCompletenessStatus,
    ContextScope,
)
from app.domain.memory.intelligence.registry import ContextDescriptor


class ContextValidationError(Exception):
    """Base exception for context validation errors."""
    pass


class CrossWorkspaceContextError(ContextValidationError):
    """Raised when an entity or relationship breaches tenant workspace boundaries."""
    pass


class MissingRequiredContextError(ContextValidationError):
    """Raised when mandatory blocks are absent in strict mode."""
    pass


class ContextValidator:
    """
    Validates composed context components deterministically.
    Never hallucinates or synthesizes missing data.
    """

    def validate_workspace_isolation(
        self,
        workspace_id: Optional[uuid.UUID],
        memory_data: Optional[Dict[str, Any]],
        relationships_data: Optional[List[Dict[str, Any]]],
        strict: bool = True,
    ) -> List[str]:
        """
        Ensure all entities and relationships belong strictly to the requested workspace.
        """
        violations: List[str] = []
        if not workspace_id:
            return violations

        target_ws_str = str(workspace_id)

        # Check memory record
        if memory_data:
            rec_ws = str(memory_data.get("workspace_id", ""))
            if rec_ws and rec_ws != target_ws_str:
                msg = f"Memory record workspace ({rec_ws}) does not match target ({target_ws_str})"
                violations.append(msg)
                if strict:
                    raise CrossWorkspaceContextError(msg)

        # Check relationships
        if relationships_data:
            for idx, rel in enumerate(relationships_data):
                rel_ws = str(rel.get("workspace_id", ""))
                if rel_ws and rel_ws != target_ws_str:
                    msg = f"Relationship at index {idx} workspace ({rel_ws}) does not match target ({target_ws_str})"
                    violations.append(msg)
                    if strict:
                        raise CrossWorkspaceContextError(msg)

        return violations

    def evaluate_completeness(
        self,
        descriptor: Optional[ContextDescriptor],
        requested_blocks: List[ContextBlockType],
        loaded_blocks: Dict[ContextBlockType, Dict[str, Any]],
        errors: Optional[Dict[ContextBlockType, str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> ContextCompletenessReport:
        """
        Evaluate context completeness and data quality without guessing missing information.
        """
        all_warnings: List[str] = list(warnings or [])
        missing_fields: List[str] = []
        errs = errors or {}

        total_requested = len(requested_blocks)
        loaded_count = 0

        for b in requested_blocks:
            data = loaded_blocks.get(b)
            if data is not None and not errs.get(b):
                # Basic check on non-empty payload
                if isinstance(data, (dict, list)) and len(data) > 0:
                    loaded_count += 1
                elif data is True or isinstance(data, (int, float)):
                    loaded_count += 1
                else:
                    all_warnings.append(f"Block '{b.value}' returned empty payload")
                    missing_fields.append(f"block:{b.value}")
            else:
                missing_fields.append(f"block:{b.value}")
                if errs.get(b):
                    all_warnings.append(f"Block '{b.value}' failed to load: {errs[b]}")

        # Check descriptor required blocks
        if descriptor and descriptor.required_blocks:
            for req_b in descriptor.required_blocks:
                if req_b not in loaded_blocks or not loaded_blocks[req_b] or errs.get(req_b):
                    missing_fields.append(f"required_block:{req_b.value}")
                    all_warnings.append(f"Mandatory required block '{req_b.value}' is missing or empty")

        score = (loaded_count / total_requested) if total_requested > 0 else 1.0

        if score >= 0.99 and not all_warnings:
            status = ContextCompletenessStatus.COMPLETE
        elif score >= 0.5:
            status = ContextCompletenessStatus.PARTIAL
        elif score > 0.0:
            status = ContextCompletenessStatus.INCOMPLETE
        else:
            status = ContextCompletenessStatus.DEGRADED

        if all_warnings and status == ContextCompletenessStatus.COMPLETE:
            status = ContextCompletenessStatus.PARTIAL

        is_valid = True
        if descriptor and descriptor.required_blocks:
            for req_b in descriptor.required_blocks:
                if req_b not in loaded_blocks or not loaded_blocks[req_b]:
                    is_valid = False
                    break

        return ContextCompletenessReport(
            score=min(1.0, max(0.0, score)),
            status=status,
            total_blocks_requested=total_requested,
            blocks_loaded=loaded_count,
            missing_fields=missing_fields,
            warnings=all_warnings,
            is_valid=is_valid,
        )


default_context_validator = ContextValidator()
