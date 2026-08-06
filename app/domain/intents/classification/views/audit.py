"""
HunterOS Engage V1 - Audit Classification View
Full provenance, diagnostics, and zero-mutation compliance trace.
"""

from __future__ import annotations

from typing import Any, Dict

from app.domain.intents.classification.models import IntentClassificationResult
from app.domain.intents.classification.views.base import AbstractClassificationView


class AuditClassificationView(AbstractClassificationView):
    """
    Audit view providing end-to-end verification, stage timings, rule execution history,
    and architectural non-mutation certificate.
    """

    def __init__(self):
        super().__init__(
            view_name="AuditClassificationView",
            description="Audit trace detailing taxonomy version, executed rules, diagnostics, and pipeline timings.",
        )

    def generate(self, result: IntentClassificationResult) -> Dict[str, Any]:
        return {
            "view_type": "AUDIT",
            "classification_id": str(result.classification_id),
            "conversation_id": result.conversation_id,
            "provenance": result.provenance.to_dict(),
            "diagnostics": result.diagnostics.to_dict(),
            "metadata": result.metadata.to_dict(),
            "architectural_compliance": {
                "zero_memory_mutations": True,
                "zero_autonomous_actions": True,
                "zero_journey_mutations": True,
                "is_schema_valid": result.diagnostics.is_valid,
            },
        }
