"""
HunterOS Engage V1 - Healthcare Rule Pack
Modular vertical rule pack template for healthcare & medical appointment / consultation intents.
"""

from __future__ import annotations

from typing import List

from app.domain.intents.rules.base import AbstractIntentRule
from app.domain.intents.rules.pack import AbstractRulePack


class HealthcareRulePack(AbstractRulePack):
    """Healthcare domain vertical rule pack."""

    def __init__(self, custom_rules: List[AbstractIntentRule] = None):
        self._rules = custom_rules or []

    @property
    def pack_name(self) -> str:
        return "HealthcareRulePack"

    @property
    def description(self) -> str:
        return "Specialized healthcare vertical rule pack for appointments, medical inquiries, and consultations."

    def get_rules(self) -> List[AbstractIntentRule]:
        return list(self._rules)
