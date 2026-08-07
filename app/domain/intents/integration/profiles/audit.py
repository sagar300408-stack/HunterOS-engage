"""
HunterOS Engage V1 - Audit Composition Profile
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.intents.integration.models import CompositionProfileType, IntentIntelligenceContext
from app.domain.intents.integration.profiles.full import FullProfile


class AuditProfile(FullProfile):
    """Composition profile synthesizing full governance and execution audit trace."""

    def __init__(self) -> None:
        super().__init__()
        self.profile_name = "AuditProfile"
        self.profile_type = CompositionProfileType.AUDIT
        self.description = "Audit and governance perspective with complete rule logs, evidence IDs, and DAG snapshots."

    def apply(self, context: IntentIntelligenceContext, options: Optional[Dict[str, Any]] = None) -> None:
        context.audit_view = self._build_audit_view(context)
