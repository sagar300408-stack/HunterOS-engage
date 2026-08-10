from __future__ import annotations

class RecommendationBaseError(Exception):
    """Base exception for recommendations domain."""

class RecommendationNotFoundError(RecommendationBaseError):
    """Raised when a recommendation cannot be found."""

class RecommendationValidationError(RecommendationBaseError):
    """Raised when recommendation data is invalid."""

class RecommendationWorkspaceIsolationError(RecommendationBaseError):
    """Raised on workspace cross-access violations."""

class RecommendationLifecycleError(RecommendationBaseError):
    """Raised on invalid lifecycle transitions."""

class InvalidRecommendationTypeError(RecommendationBaseError):
    """Raised on invalid recommendation type."""

class InvalidRecommendationStatusError(RecommendationBaseError):
    """Raised on invalid recommendation status."""

class InvalidRecommendationEvidenceError(RecommendationBaseError):
    """Raised on invalid recommendation evidence."""

class InvalidRecommendationProvenanceError(RecommendationBaseError):
    """Raised on invalid recommendation provenance."""

class DuplicateRecommendationError(RecommendationBaseError):
    """Raised when a duplicate recommendation is detected."""

class RecommendationConflictError(RecommendationBaseError):
    """Raised on concurrent modification conflicts."""

class RecommendationImmutableFieldError(RecommendationBaseError):
    """Raised when trying to modify an immutable field."""
