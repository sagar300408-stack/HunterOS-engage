"""
HunterOS Engage V1 — Customer Journey Validation Framework
Phase 2.4.1 & 2.4.2: Journey Validation
"""

from __future__ import annotations

import uuid
from typing import List, Optional, Union

from app.domain.journey.exceptions import (
    DuplicateTransitionError,
    InvalidEvidenceError,
    InvalidTransitionError,
    JourneyDefinitionError,
    JourneyError,
    StageValidationError,
    TerminalStageError,
    WorkspaceIsolationError,
)
from app.domain.journey.context import JourneyProgressionContext
from app.domain.journey.models import (
    JourneyDefinition,
    JourneyEvidence,
    JourneyStageCode,
    JourneyStageTransition,
    JourneyState,
)


class JourneyValidationFramework:
    """Framework for validating journey progressions, definitions, and states."""

    def validate_workspace_isolation(
        self,
        workspace_id: Union[uuid.UUID, str],
        journey_state_or_evidence: Union[JourneyState, JourneyEvidence, List[JourneyEvidence]],
    ) -> List[str]:
        """Validate that journey state and evidence belong to the specified workspace."""
        errors: List[str] = []
        target_ws = str(workspace_id)

        if isinstance(journey_state_or_evidence, JourneyState):
            if str(journey_state_or_evidence.workspace_id) != target_ws:
                msg = f"Journey workspace {journey_state_or_evidence.workspace_id} does not match {target_ws}"
                errors.append(msg)
                raise WorkspaceIsolationError(msg)
        elif isinstance(journey_state_or_evidence, JourneyEvidence):
            ev_ws = journey_state_or_evidence.metadata.get("workspace_id")
            if ev_ws is not None and str(ev_ws) != target_ws:
                msg = f"Evidence workspace {ev_ws} does not match {target_ws}"
                errors.append(msg)
                raise WorkspaceIsolationError(msg)
        elif isinstance(journey_state_or_evidence, list):
            for ev in journey_state_or_evidence:
                ev_ws = ev.metadata.get("workspace_id")
                if ev_ws is not None and str(ev_ws) != target_ws:
                    msg = f"Evidence workspace {ev_ws} does not match {target_ws}"
                    errors.append(msg)
                    raise WorkspaceIsolationError(msg)

        return errors

    def validate_journey_definition(self, definition: JourneyDefinition) -> List[str]:
        """Validate the structural integrity of a JourneyDefinition."""
        errors: List[str] = []
        if not definition.entry_stage:
            errors.append("Journey definition is missing entry_stage.")

        stage_codes = {sd.stage_code for sd in definition.stage_definitions}
        if definition.entry_stage not in stage_codes:
            errors.append(f"Entry stage {definition.entry_stage} not in defined stages.")

        terminal_stages = [sd.stage_code for sd in definition.stage_definitions if sd.is_terminal]
        if not terminal_stages:
            errors.append("Journey definition must have at least one terminal stage.")

        reachable_stages = set()
        for sd in definition.stage_definitions:
            for next_stage in sd.allowed_next_stages:
                if next_stage not in stage_codes:
                    errors.append(f"Stage {sd.stage_code} references unknown next stage {next_stage}")
                reachable_stages.add(next_stage)

        for code in stage_codes:
            if code != definition.entry_stage and code not in reachable_stages:
                errors.append(f"Stage {code} is an orphan stage.")

        if errors:
            raise JourneyDefinitionError("; ".join(errors))

        return errors

    def validate_stage_transition(
        self,
        from_stage: JourneyStageCode,
        to_stage: JourneyStageCode,
        definition: JourneyDefinition,
    ) -> List[str]:
        """Validate if a transition from from_stage to to_stage is allowed by definition."""
        errors: List[str] = []
        from_def = definition.get_stage_definition(from_stage)
        if from_def is None:
            msg = f"Unknown from_stage {from_stage}"
            errors.append(msg)
            raise StageValidationError(msg)

        if from_def.is_terminal:
            msg = f"Cannot transition from terminal stage {from_stage}"
            errors.append(msg)
            raise TerminalStageError(msg)

        if to_stage not in from_def.allowed_next_stages:
            msg = f"Transition from {from_stage} to {to_stage} is not allowed."
            errors.append(msg)
            raise InvalidTransitionError(msg)

        return errors

    def validate_terminal_stage(
        self,
        current_stage: JourneyStageCode,
        definition: Optional[JourneyDefinition] = None,
    ) -> List[str]:
        """Validate whether current_stage is a terminal stage from which transitions are blocked."""
        errors: List[str] = []
        if definition is not None:
            stage_def = definition.get_stage_definition(current_stage)
            if stage_def and stage_def.is_terminal:
                msg = f"Cannot transition from terminal stage {current_stage}."
                errors.append(msg)
                raise TerminalStageError(msg)
        else:
            # Common terminal stage codes
            terminal_codes = {
                JourneyStageCode.CLOSED_WON,
                JourneyStageCode.CLOSED_LOST,
                JourneyStageCode.INACTIVE,
            }
            if current_stage in terminal_codes:
                msg = f"Cannot transition from terminal stage {current_stage}."
                errors.append(msg)
                raise TerminalStageError(msg)

        return errors

    def validate_evidence_integrity(self, evidence_list: List[JourneyEvidence]) -> List[str]:
        """Validate evidence elements for presence, types, and timestamps."""
        errors: List[str] = []
        if not evidence_list:
            msg = "Evidence list cannot be empty."
            errors.append(msg)
            raise InvalidEvidenceError(msg)

        for ev in evidence_list:
            if not ev.evidence_id:
                errors.append("Evidence must have an evidence_id.")
            if not ev.evidence_type:
                errors.append("Evidence must have an evidence_type.")
            if not ev.timestamp:
                errors.append("Evidence must have a timestamp.")

        if any("must have" in err for err in errors):
            raise InvalidEvidenceError("; ".join(errors))

        return errors

    def validate_timestamp_ordering(self, transitions: List[JourneyStageTransition]) -> List[str]:
        """Ensure transitions occur in chronological order."""
        errors: List[str] = []
        for i in range(1, len(transitions)):
            if transitions[i].occurred_at < transitions[i - 1].occurred_at:
                errors.append(
                    f"Transition {transitions[i].transition_id} occurs before {transitions[i - 1].transition_id}."
                )
        return errors

    def validate_duplicate_transition(
        self,
        transitions: List[JourneyStageTransition],
        new_from: Optional[JourneyStageCode],
        new_to: JourneyStageCode,
        new_evidence_ids: List[str],
    ) -> List[str]:
        """Detect and reject duplicate transitions with identical evidence."""
        errors: List[str] = []
        new_evidence_set = set(new_evidence_ids)
        for t in transitions:
            if t.from_stage == new_from and t.to_stage == new_to:
                existing_evidence_set = {str(e.evidence_id) for e in t.evidence}
                if existing_evidence_set and new_evidence_set and existing_evidence_set == new_evidence_set:
                    msg = f"Duplicate transition from {new_from} to {new_to} with identical evidence."
                    errors.append(msg)
                    raise DuplicateTransitionError(msg)
        return errors

    def validate_confidence_bounds(self, confidence: float) -> List[str]:
        """Ensure confidence is between 0.0 and 1.0."""
        errors: List[str] = []
        if not (0.0 <= confidence <= 1.0):
            msg = f"Confidence {confidence} out of bounds [0.0, 1.0]."
            errors.append(msg)
            raise InvalidEvidenceError(msg)
        return errors

    def validate_entity_consistency(
        self,
        journey_state: JourneyState,
        entity_type: str,
        entity_id: str,
    ) -> List[str]:
        """Ensure entity identity consistency."""
        errors: List[str] = []
        if journey_state.entity_type != entity_type:
            msg = f"Entity type mismatch: {journey_state.entity_type} != {entity_type}"
            errors.append(msg)
            raise JourneyError(msg)
        if journey_state.entity_id != entity_id:
            msg = f"Entity ID mismatch: {journey_state.entity_id} != {entity_id}"
            errors.append(msg)
            raise JourneyError(msg)
        return errors

    def validate_progression(self, context: JourneyProgressionContext) -> List[str]:
        """Run all progression validation rules on context."""
        all_errors: List[str] = []

        if context.journey_state is not None and context.workspace_id is not None:
            try:
                all_errors.extend(
                    self.validate_workspace_isolation(context.workspace_id, context.journey_state)
                )
            except WorkspaceIsolationError as e:
                all_errors.append(str(e))

        if context.journey_state is not None:
            try:
                all_errors.extend(
                    self.validate_entity_consistency(
                        context.journey_state, context.entity_type, context.entity_id
                    )
                )
            except JourneyError as e:
                all_errors.append(str(e))

        if context.journey_definition is not None:
            try:
                all_errors.extend(self.validate_journey_definition(context.journey_definition))
            except JourneyDefinitionError as e:
                all_errors.append(str(e))

            if context.journey_state is not None:
                try:
                    all_errors.extend(
                        self.validate_terminal_stage(
                            context.journey_state.current_stage, context.journey_definition
                        )
                    )
                except TerminalStageError as e:
                    all_errors.append(str(e))

        return all_errors


# Global instance
default_validator: JourneyValidationFramework = JourneyValidationFramework()


# Helper functions
def validate_workspace_isolation(
    workspace_id: Union[uuid.UUID, str],
    journey_state_or_evidence: Union[JourneyState, JourneyEvidence, List[JourneyEvidence]],
) -> List[str]:
    return default_validator.validate_workspace_isolation(workspace_id, journey_state_or_evidence)


def validate_stage_transition(
    from_stage: JourneyStageCode,
    to_stage: JourneyStageCode,
    definition: JourneyDefinition,
) -> List[str]:
    return default_validator.validate_stage_transition(from_stage, to_stage, definition)


def validate_terminal_stage(
    current_stage: JourneyStageCode,
    definition: Optional[JourneyDefinition] = None,
) -> List[str]:
    return default_validator.validate_terminal_stage(current_stage, definition)


def validate_evidence_integrity(evidence_list: List[JourneyEvidence]) -> List[str]:
    return default_validator.validate_evidence_integrity(evidence_list)


def validate_confidence_bounds(confidence: float) -> List[str]:
    return default_validator.validate_confidence_bounds(confidence)


def validate_entity_consistency(
    journey_state: JourneyState,
    entity_type: str,
    entity_id: str,
) -> List[str]:
    return default_validator.validate_entity_consistency(journey_state, entity_type, entity_id)
