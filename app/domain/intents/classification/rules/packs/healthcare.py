"""
HunterOS Engage V1 - Healthcare Classification Rule Pack
Specialized healthcare intent classification rules.
"""

from __future__ import annotations

from typing import List, Optional

from app.domain.intents.classification.canonical.models import CanonicalIntent
from app.domain.intents.classification.context import IntentClassificationContext
from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
)
from app.domain.intents.classification.rules.base import (
    AbstractClassificationRule,
    AbstractClassificationRulePack,
    ClassificationCandidate,
)


class DoctorAppointmentRule(AbstractClassificationRule):
    def __init__(self, rule_version: str = "1.0.0"):
        super().__init__(
            rule_name="DoctorAppointmentRule",
            rule_version=rule_version,
            description="Classifies doctor appointments and clinic consultations into Healthcare domain.",
        )

    def evaluate(
        self,
        canonical: CanonicalIntent,
        context: IntentClassificationContext,
    ) -> Optional[ClassificationCandidate]:
        raw = (canonical.canonical_name + " " + canonical.normalized_title + " " + canonical.normalized_description).lower()
        if any(k in raw for k in ["doctor", "clinic", "hospital", "physician", "patient", "consultation"]):
            return ClassificationCandidate(
                category=IntentCategory.OPERATIONAL,
                domain=BusinessDomain.HEALTHCARE,
                process="HEALTHCARE_INTAKE",
                taxonomy_node_id="operational.meeting_request",
                confidence_boost=0.08,
                aliases=["DOCTOR_APPOINTMENT", "PATIENT_INTAKE"],
            )
        return None


class HealthcareClassificationRulePack(AbstractClassificationRulePack):
    """
    Healthcare vertical rule pack.
    """

    def __init__(self, version: str = "1.0.0"):
        super().__init__(
            pack_name="HealthcareClassificationRulePack",
            version=version,
            description="Healthcare vertical intent classification rules.",
        )
        self._rules: List[AbstractClassificationRule] = [
            DoctorAppointmentRule(rule_version=version),
        ]

    def get_rules(self) -> List[AbstractClassificationRule]:
        return list(self._rules)
