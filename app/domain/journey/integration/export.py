from __future__ import annotations

from typing import Any, Dict

class JourneyContextExportEngine:
    def __init__(self) -> None:
        pass

    def to_standard_api_dto(self, context: Any) -> Dict[str, Any]:
        """Transforms context to a Standard API DTO."""
        return {
            "context_id": getattr(context, "context_id", ""),
            "workspace_id": getattr(context, "workspace_id", ""),
            "entity_id": getattr(context, "entity_id", ""),
            "journey_type": getattr(context, "journey_type", ""),
            "generated_at": getattr(context, "generated_at", None),
            "context_version": getattr(context, "context_version", ""),
            "data": getattr(context, "data", {})
        }

    def to_executive_dto(self, context: Any) -> Dict[str, Any]:
        """Transforms context to an Executive DTO."""
        return {
            "summary": "Executive summary of the journey context",
            "journey_type": getattr(context, "journey_type", ""),
            "status": "Active" # deterministic fallback
        }

    def to_dashboard_dto(self, context: Any) -> Dict[str, Any]:
        """Transforms context to a Dashboard DTO."""
        return {
            "journey_id": getattr(context, "context_id", ""),
            "metrics": {},
            "timeline": []
        }

    def to_ai_ready_dto(self, context: Any) -> Dict[str, Any]:
        """
        Transforms context to an AI Ready DTO.
        Provides structured context suitable for future AI system consumption.
        No recommendations or predictions are included.
        """
        return {
            "structured_context": getattr(context, "data", {}),
            "metadata": {
                "journey_type": getattr(context, "journey_type", ""),
                "entity_id": getattr(context, "entity_id", "")
            }
        }
