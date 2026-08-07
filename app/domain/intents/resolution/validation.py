"""
HunterOS Engage V1 - Multi-Intent Resolution Validation Guardrails
Zero-trust integrity checks for graph relationships, dependencies, conflicts, groups, and tenant isolation.
"""

from __future__ import annotations

from typing import List, Set
import uuid

from app.domain.intents.resolution.context import MultiIntentResolutionContext
from app.domain.intents.resolution.models import (
    IntentConflict,
    IntentConflictSeverity,
    IntentDependency,
    IntentNode,
    IntentRelationship,
    IntentResolutionGroup,
)


class ResolutionValidationError(Exception):
    """Exception raised when resolution validation guardrails fail."""
    pass


class MultiIntentResolutionValidator:
    """
    Zero-trust validator for multi-intent resolution models and pipelines.
    Enforces referential integrity, acyclicity, workspace isolation, and evidence completeness.
    """

    def validate(self, context: MultiIntentResolutionContext) -> bool:
        """Run all resolution validation guardrails."""
        self.validate_workspace_isolation(context)
        self.validate_relationship_consistency(context)
        self.validate_dependency_consistency(context)
        self.validate_conflict_integrity(context)
        self.validate_group_integrity(context)
        self.validate_evidence_completeness(context)
        return len(context.validation_errors) == 0

    def validate_workspace_isolation(self, context: MultiIntentResolutionContext) -> None:
        """Enforce strict multi-tenant workspace isolation."""
        if context.workspace_id is None:
            return

        expected_ws = context.workspace_id

        if context.detection_result and context.detection_result.workspace_id:
            if context.detection_result.workspace_id != expected_ws:
                context.add_validation_error(
                    f"Workspace isolation violation: DetectionResult workspace "
                    f"'{context.detection_result.workspace_id}' does not match context workspace '{expected_ws}'"
                )

        if context.classification_result and context.classification_result.workspace_id:
            if context.classification_result.workspace_id != expected_ws:
                context.add_validation_error(
                    f"Workspace isolation violation: ClassificationResult workspace "
                    f"'{context.classification_result.workspace_id}' does not match context workspace '{expected_ws}'"
                )

        if context.evolution_result and context.evolution_result.workspace_id:
            if context.evolution_result.workspace_id != expected_ws:
                context.add_validation_error(
                    f"Workspace isolation violation: EvolutionResult workspace "
                    f"'{context.evolution_result.workspace_id}' does not match context workspace '{expected_ws}'"
                )

    def validate_relationship_consistency(self, context: MultiIntentResolutionContext) -> None:
        """Validate relationship edges against graph nodes."""
        node_keys: Set[str] = set(context.normalized_nodes.keys())

        for rel in context.analyzed_relationships:
            src_str = str(rel.source_intent_id)
            tgt_str = str(rel.target_intent_id)

            if src_str == tgt_str:
                context.add_validation_error(
                    f"Relationship self-loop invalid: intent '{src_str}' cannot relate to itself"
                )

            if src_str not in node_keys:
                context.add_validation_error(
                    f"Relationship source '{src_str}' does not exist in normalized intent graph"
                )

            if tgt_str not in node_keys:
                context.add_validation_error(
                    f"Relationship target '{tgt_str}' does not exist in normalized intent graph"
                )

            if not (0.0 <= rel.strength <= 1.0):
                context.add_validation_error(
                    f"Relationship strength {rel.strength} out of bounds [0.0, 1.0] for relationship {rel.relationship_id}"
                )

    def validate_dependency_consistency(self, context: MultiIntentResolutionContext) -> None:
        """Validate dependency links and enforce acyclicity."""
        node_keys: Set[str] = set(context.normalized_nodes.keys())

        # Validate all dependencies
        deps = list(context.analyzed_dependencies)
        if context.resolution_graph and context.resolution_graph.dependencies:
            deps = list(context.resolution_graph.dependencies)

        for dep in deps:
            src_str = str(dep.source_intent_id)
            tgt_str = str(dep.target_intent_id)

            if src_str == tgt_str:
                context.add_validation_error(
                    f"Self-dependency invalid: intent '{src_str}' cannot depend on itself"
                )

            if src_str not in node_keys:
                context.add_validation_error(
                    f"Dependency prerequisite '{src_str}' does not exist in normalized intent graph"
                )

            if tgt_str not in node_keys:
                context.add_validation_error(
                    f"Dependency target '{tgt_str}' does not exist in normalized intent graph"
                )

        # Check for dependency cycles across all dependencies
        if deps:
            adj: Dict[str, List[str]] = {}
            for d in deps:
                adj.setdefault(str(d.source_intent_id), []).append(str(d.target_intent_id))

            visited: Set[str] = set()
            rec_stack: Set[str] = set()

            def dfs(node: str) -> bool:
                visited.add(node)
                rec_stack.add(node)
                for neighbor in adj.get(node, []):
                    if neighbor not in visited:
                        if not dfs(neighbor):
                            return False
                    elif neighbor in rec_stack:
                        return False
                rec_stack.remove(node)
                return True

            has_cycle = False
            for n in list(adj.keys()):
                if n not in visited:
                    if not dfs(n):
                        has_cycle = True
                        break

            if has_cycle:
                context.add_validation_error(
                    "Cyclic dependency detected: Intent dependencies must form a directed acyclic graph (DAG)"
                )

    def validate_conflict_integrity(self, context: MultiIntentResolutionContext) -> None:
        """Validate conflict references and intent IDs."""
        node_keys: Set[str] = set(context.normalized_nodes.keys())

        for conflict in context.analyzed_conflicts:
            if not conflict.intent_ids:
                context.add_validation_error(
                    f"Conflict {conflict.conflict_id} contains no participating intent IDs"
                )
                continue

            for iid in conflict.intent_ids:
                if str(iid) not in node_keys:
                    context.add_validation_error(
                        f"Conflict intent ID '{iid}' does not exist in normalized intent graph"
                    )

    def validate_group_integrity(self, context: MultiIntentResolutionContext) -> None:
        """Validate resolution group structures and dominance disjointness."""
        seen_group_ids: Set[uuid.UUID] = set()

        for group in context.resolved_groups:
            if group.group_id in seen_group_ids:
                context.add_validation_error(
                    f"Duplicate group_id '{group.group_id}' detected"
                )
            seen_group_ids.add(group.group_id)

            supporting_ids = {s.intent_id for s in group.supporting_intents}
            all_ids = set(group.all_intent_ids)

            if group.dominant_intent:
                dom_id = group.dominant_intent.intent_id
                if dom_id in supporting_ids:
                    context.add_validation_error(
                        f"Dominant intent '{dom_id}' cannot simultaneously be in supporting_intents for group '{group.name}'"
                    )
                if dom_id not in all_ids:
                    context.add_validation_error(
                        f"Dominant intent '{dom_id}' must be included in all_intent_ids for group '{group.name}'"
                    )

            for sid in supporting_ids:
                if sid not in all_ids:
                    context.add_validation_error(
                        f"Supporting intent '{sid}' must be included in all_intent_ids for group '{group.name}'"
                    )

    def validate_evidence_completeness(self, context: MultiIntentResolutionContext) -> None:
        """Validate that high-severity conflicts and blocking dependencies have justification."""
        for conflict in context.analyzed_conflicts:
            if conflict.severity in (IntentConflictSeverity.HIGH, IntentConflictSeverity.CRITICAL):
                if not conflict.description and not conflict.evidence_ids:
                    context.add_warning(
                        f"High/Critical severity conflict {conflict.conflict_id} missing descriptive reason or evidence"
                    )

        for dep in context.analyzed_dependencies:
            if dep.is_blocking and not dep.reason and not dep.evidence_ids:
                context.add_warning(
                    f"Blocking dependency {dep.dependency_id} missing rationale or evidence references"
                )
