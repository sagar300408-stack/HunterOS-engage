"""
HunterOS Engage — Append-Only Memory Audit Service

Responsible for all audit trail generation:
  1. Immutable Aggregate Snapshots (CustomerMemoryVersion with SHA-256 hash)
  2. Append-Only Chronological Timeline Events (CustomerMemoryTimelineEvent)
  3. Granular Field-Level Change Logs (MemoryChangeLog with changed_module attribution)

Strict Invariant: All audit tables are APPEND-ONLY. No updates or deletes.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.models import (
    ChangeType,
    CustomerMemory,
    CustomerMemoryTimelineEvent,
    CustomerMemoryVersion,
    LifecycleStatus,
    MemoryChangeLog,
    MemoryImportance,
    MemoryTimelineCategory,
)


class MemoryAuditService:
    """
    Centralized, independent, append-only audit service for CustomerMemory Aggregate Root.
    """

    @staticmethod
    def compute_snapshot_hash(payload: Dict[str, Any]) -> str:
        """Computes a deterministic SHA-256 checksum of the normalized JSON payload."""
        normalized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_memory_diff(
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        prefix: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Recursively compares old and new state dictionaries.
        Returns a list of granular field changes with path, old_val, new_val, change_type.
        """
        changes: List[Dict[str, Any]] = []
        all_keys = set(old_data.keys()).union(set(new_data.keys()))

        for key in sorted(all_keys):
            current_path = f"{prefix}.{key}" if prefix else key
            in_old = key in old_data
            in_new = key in new_data

            if in_old and not in_new:
                changes.append({
                    "field_path": current_path,
                    "old_value": old_data[key],
                    "new_value": None,
                    "change_type": ChangeType.DELETED,
                })
            elif not in_old and in_new:
                changes.append({
                    "field_path": current_path,
                    "old_value": None,
                    "new_value": new_data[key],
                    "change_type": ChangeType.ADDED,
                })
            else:
                old_val = old_data[key]
                new_val = new_data[key]

                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    nested = MemoryAuditService.compute_memory_diff(
                        old_val, new_val, prefix=current_path
                    )
                    changes.extend(nested)
                elif old_val != new_val:
                    changes.append({
                        "field_path": current_path,
                        "old_value": old_val,
                        "new_value": new_val,
                        "change_type": ChangeType.MODIFIED,
                    })

        return changes

    @staticmethod
    def _categorize_field_path(field_path: str) -> MemoryTimelineCategory:
        """Maps modified field paths to business timeline categories."""
        root = field_path.split(".")[0].lower()
        mapping = {
            "financial_info": MemoryTimelineCategory.FINANCIAL,
            "property_info": MemoryTimelineCategory.PREFERENCE,
            "personal_info": MemoryTimelineCategory.PROFILE,
            "identity": MemoryTimelineCategory.PROFILE,
            "relationship_info": MemoryTimelineCategory.RELATIONSHIP,
            "communication_preferences": MemoryTimelineCategory.PREFERENCE,
            "behavioral_attributes": MemoryTimelineCategory.PREFERENCE,
            "journey_snapshot": MemoryTimelineCategory.LIFECYCLE,
            "metadata": MemoryTimelineCategory.SYSTEM,
        }
        return mapping.get(root, MemoryTimelineCategory.PROFILE)

    async def record_creation_audit(
        self,
        session: AsyncSession,
        memory: CustomerMemory,
        actor: Optional[str] = "system",
        source: str = "API",
        reason: Optional[str] = "Customer memory initialized",
    ) -> CustomerMemoryVersion:
        """
        Creates baseline v1 Aggregate Snapshot, initial timeline event, and baseline change logs.
        """
        payload = memory.memory_payload or {}
        snapshot_hash = self.compute_snapshot_hash(payload)

        # 1. Version Snapshot v1
        version = CustomerMemoryVersion(
            customer_id=memory.customer_id,
            memory_id=memory.id,
            version_number=1,
            snapshot_data=payload,
            schema_version="1.0.0",
            snapshot_hash=snapshot_hash,
            reason=reason,
            trigger="initial_creation",
            created_by=actor,
            created_at=datetime.now(timezone.utc),
        )
        session.add(version)

        # 2. Timeline Event
        timeline_event = CustomerMemoryTimelineEvent(
            customer_id=memory.customer_id,
            memory_id=memory.id,
            category=MemoryTimelineCategory.LIFECYCLE,
            event_type="memory_created",
            title="Customer Memory Created",
            description="Foundational customer memory initialized.",
            source=source,
            importance=MemoryImportance.HIGH,
            payload={"initial_blocks": list(payload.keys())},
            version_number=1,
            created_at=datetime.now(timezone.utc),
        )
        session.add(timeline_event)

        # 3. Initial Change Logs for non-empty fields
        diffs = self.compute_memory_diff({}, payload)
        for diff in diffs:
            log_item = MemoryChangeLog(
                customer_id=memory.customer_id,
                memory_id=memory.id,
                version_number=1,
                field_path=diff["field_path"],
                old_value=diff["old_value"],
                new_value=diff["new_value"],
                change_type=diff["change_type"],
                changed_module="MemoryInitialization",
                changed_by=actor,
                created_at=datetime.now(timezone.utc),
            )
            session.add(log_item)

        return version

    async def record_update_audit(
        self,
        session: AsyncSession,
        memory: CustomerMemory,
        old_payload: Dict[str, Any],
        new_payload: Dict[str, Any],
        actor: Optional[str] = "system",
        changed_module: str = "API",
        trigger: str = "manual_update",
        reason: Optional[str] = "Customer profile update",
    ) -> CustomerMemoryVersion:
        """
        Records an update audit:
          - Generates immutable Aggregate Snapshot (CustomerMemoryVersion)
          - Emits granular field-level MemoryChangeLog records
          - Emits categorized CustomerMemoryTimelineEvent records
        """
        snapshot_hash = self.compute_snapshot_hash(new_payload)

        # 1. Version Snapshot
        version = CustomerMemoryVersion(
            customer_id=memory.customer_id,
            memory_id=memory.id,
            version_number=memory.version_number,
            snapshot_data=new_payload,
            schema_version="1.0.0",
            snapshot_hash=snapshot_hash,
            reason=reason,
            trigger=trigger,
            created_by=actor,
            created_at=datetime.now(timezone.utc),
        )
        session.add(version)

        # 2. Field Change Logs
        diffs = self.compute_memory_diff(old_payload, new_payload)
        for diff in diffs:
            log_item = MemoryChangeLog(
                customer_id=memory.customer_id,
                memory_id=memory.id,
                version_number=memory.version_number,
                field_path=diff["field_path"],
                old_value=diff["old_value"],
                new_value=diff["new_value"],
                change_type=diff["change_type"],
                changed_module=changed_module,
                changed_by=actor,
                created_at=datetime.now(timezone.utc),
            )
            session.add(log_item)

        # 3. Categorized Timeline Events
        if diffs:
            # Group modified fields by category
            category_counts: Dict[MemoryTimelineCategory, List[str]] = {}
            for diff in diffs:
                cat = self._categorize_field_path(diff["field_path"])
                category_counts.setdefault(cat, []).append(diff["field_path"])

            for cat, changed_paths in category_counts.items():
                title = f"Memory Updated: {cat.value.title()}"
                desc = f"Updated {len(changed_paths)} fields: {', '.join(changed_paths[:3])}"
                if len(changed_paths) > 3:
                    desc += f" and {len(changed_paths) - 3} more"

                tl_event = CustomerMemoryTimelineEvent(
                    customer_id=memory.customer_id,
                    memory_id=memory.id,
                    category=cat,
                    event_type="memory_updated",
                    title=title,
                    description=desc,
                    source=changed_module,
                    importance=MemoryImportance.MEDIUM,
                    payload={"changed_paths": changed_paths, "diff_count": len(changed_paths)},
                    version_number=memory.version_number,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(tl_event)

        return version

    async def record_deletion_audit(
        self,
        session: AsyncSession,
        memory: CustomerMemory,
        actor: Optional[str] = "system",
        reason: Optional[str] = "Memory soft-deleted",
    ) -> None:
        """Emits timeline event for soft deletion."""
        tl_event = CustomerMemoryTimelineEvent(
            customer_id=memory.customer_id,
            memory_id=memory.id,
            category=MemoryTimelineCategory.LIFECYCLE,
            event_type="memory_soft_deleted",
            title="Customer Memory Soft-Deleted",
            description=reason or "Customer memory record marked as soft-deleted.",
            source="MemoryLifecycleEngine",
            importance=MemoryImportance.CRITICAL,
            payload={"reason": reason, "deleted_by": actor},
            version_number=memory.version_number,
            created_at=datetime.now(timezone.utc),
        )
        session.add(tl_event)

    async def record_restoration_audit(
        self,
        session: AsyncSession,
        memory: CustomerMemory,
        actor: Optional[str] = "system",
        reason: Optional[str] = "Memory restored",
    ) -> None:
        """Emits timeline event for memory restoration."""
        tl_event = CustomerMemoryTimelineEvent(
            customer_id=memory.customer_id,
            memory_id=memory.id,
            category=MemoryTimelineCategory.LIFECYCLE,
            event_type="memory_restored",
            title="Customer Memory Restored",
            description=reason or "Soft-deleted customer memory restored to active state.",
            source="MemoryLifecycleEngine",
            importance=MemoryImportance.HIGH,
            payload={"reason": reason, "restored_by": actor},
            version_number=memory.version_number,
            created_at=datetime.now(timezone.utc),
        )
        session.add(tl_event)

    async def record_status_transition_audit(
        self,
        session: AsyncSession,
        memory: CustomerMemory,
        old_status: LifecycleStatus,
        new_status: LifecycleStatus,
        actor: Optional[str] = "system",
        reason: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Emits timeline event for lifecycle status transition."""
        tl_event = CustomerMemoryTimelineEvent(
            customer_id=memory.customer_id,
            memory_id=memory.id,
            category=MemoryTimelineCategory.LIFECYCLE,
            event_type="memory_status_changed",
            title=f"Memory Status: {new_status.value}",
            description=f"Status changed from {old_status.value} to {new_status.value}. Reason: {reason or 'N/A'}",
            source="MemoryLifecycleEngine",
            importance=MemoryImportance.HIGH,
            payload={
                "previous_status": old_status.value,
                "current_status": new_status.value,
                "reason": reason,
                "actor": actor,
                "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
            },
            version_number=memory.version_number,
            created_at=timestamp or datetime.now(timezone.utc),
        )
        session.add(tl_event)


# Module-level convenience functions
compute_snapshot_hash = MemoryAuditService.compute_snapshot_hash
compute_memory_diff = MemoryAuditService.compute_memory_diff


def deep_merge_dicts(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges updates into base dictionary."""
    result = dict(base)
    for k, v in updates.items():
        if isinstance(v, dict) and k in result and isinstance(result[k], dict):
            result[k] = deep_merge_dicts(result[k], v)
        else:
            result[k] = v
    return result


def map_field_path_to_category(field_path: str) -> MemoryTimelineCategory:
    """Maps modified field paths to business timeline categories."""
    return MemoryAuditService._categorize_field_path(field_path)


# Default AuditService singleton
_default_audit_service: Optional[MemoryAuditService] = None


def get_memory_audit_service() -> MemoryAuditService:
    global _default_audit_service
    if _default_audit_service is None:
        _default_audit_service = MemoryAuditService()
    return _default_audit_service
