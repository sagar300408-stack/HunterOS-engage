"""
HunterOS Engage V1 - Manufacturing Rule Pack
Modular vertical rule pack template for industrial & manufacturing quote, sample, and RFP intents.
"""

from __future__ import annotations

from typing import List

from app.domain.intents.rules.base import AbstractIntentRule
from app.domain.intents.rules.pack import AbstractRulePack


class ManufacturingRulePack(AbstractRulePack):
    """Manufacturing domain vertical rule pack."""

    def __init__(self, custom_rules: List[AbstractIntentRule] = None):
        self._rules = custom_rules or []

    @property
    def pack_name(self) -> str:
        return "ManufacturingRulePack"

    @property
    def description(self) -> str:
        return "Specialized manufacturing rule pack for RFPs, BOM quotes, and sample requests."

    def get_rules(self) -> List[AbstractIntentRule]:
        return list(self._rules)
