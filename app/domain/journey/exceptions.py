"""
HunterOS Engage V1 — Customer Journey Intelligence Domain Exceptions
Phase 2.4: Journey Foundation
"""

from __future__ import annotations


class JourneyError(Exception):
    """Base exception for Journey Intelligence domain."""
    pass


class JourneyNotFoundError(JourneyError):
    """Raised when a journey instance cannot be found."""
    def __init__(self, journey_id: str = "", entity_id: str = "", message: str = ""):
        self.journey_id = str(journey_id)
        self.entity_id = str(entity_id)
        if message:
            super().__init__(message)
        else:
            detail = f"journey_id={journey_id}" if journey_id else f"entity_id={entity_id}"
            super().__init__(f"Journey not found: {detail}")


class InvalidTransitionError(JourneyError):
    """Raised when a stage transition violates the journey definition."""
    def __init__(self, from_stage: str = "", to_stage: str = "", reason: str = ""):
        self.from_stage = str(from_stage)
        self.to_stage = str(to_stage)
        self.reason = reason
        if to_stage:
            msg = f"Invalid transition: {from_stage} → {to_stage}"
        else:
            msg = f"Invalid transition: {from_stage}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class WorkspaceIsolationError(JourneyError):
    """Raised when cross-workspace evidence or access is detected."""
    def __init__(self, expected_workspace: str = "", actual_workspace: str = ""):
        self.expected_workspace = str(expected_workspace)
        self.actual_workspace = str(actual_workspace)
        if actual_workspace:
            super().__init__(
                f"Workspace isolation violation: expected={expected_workspace}, "
                f"actual={actual_workspace}"
            )
        else:
            super().__init__(f"Workspace isolation violation: {expected_workspace}")


class DuplicateTransitionError(JourneyError):
    """Raised when an idempotent progression detects a duplicate."""
    def __init__(self, fingerprint: str = ""):
        self.fingerprint = str(fingerprint)
        super().__init__(f"Duplicate progression detected: fingerprint={fingerprint}")


class InvalidEvidenceError(JourneyError):
    """Raised when evidence fails integrity checks."""
    def __init__(self, reason: str = ""):
        self.reason = str(reason)
        super().__init__(f"Invalid evidence: {reason}")


class JourneyDefinitionError(JourneyError):
    """Raised when a journey definition is invalid or not found."""
    def __init__(self, reason: str = ""):
        self.reason = str(reason)
        super().__init__(f"Journey definition error: {reason}")


class StageValidationError(JourneyError):
    """Raised when stage validation fails."""
    def __init__(self, stage: str = "", reason: str = ""):
        self.stage = str(stage)
        self.reason = str(reason)
        super().__init__(f"Stage validation error for {stage}: {reason}")


class TerminalStageError(JourneyError):
    """Raised when attempting to transition from a terminal stage."""
    def __init__(self, stage: str = ""):
        self.stage = str(stage)
        super().__init__(f"Cannot transition from terminal stage: {stage}")


class JourneyValidationError(JourneyError):
    """Raised when journey maturity or state validation fails."""
    def __init__(self, reason: str = "", errors: Optional[List[str]] = None):
        self.reason = str(reason)
        self.errors = errors or []
        msg = f"Journey validation error: {reason}"
        if self.errors:
            msg += f" (errors: {', '.join(self.errors)})"
        super().__init__(msg)


class MaturityCalculationError(JourneyError):
    """Raised when journey maturity calculation encounters an unrecoverable error."""
    def __init__(self, reason: str = ""):
        self.reason = str(reason)
        super().__init__(f"Maturity calculation error: {reason}")


class InsufficientDataError(JourneyError):
    """Raised when requested calculation requires minimum data that is not met."""
    def __init__(self, reason: str = "", sample_size: int = 0, minimum_required: int = 0):
        self.reason = str(reason)
        self.sample_size = sample_size
        self.minimum_required = minimum_required
        super().__init__(
            f"Insufficient data: {reason} (sample_size={sample_size}, minimum_required={minimum_required})"
        )


class ConfigurationNotFoundError(JourneyError):
    """Raised when requested configuration version or type is not registered."""
    def __init__(self, config_key: str = ""):
        self.config_key = str(config_key)
        super().__init__(f"Configuration not found: {config_key}")

