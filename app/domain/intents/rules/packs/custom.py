"""
HunterOS Engage V1 - Custom Rule Pack
Extensible rule pack for custom enterprise plugin rules.
"""

from __future__ import annotations

from typing import List

from app.domain.intents.rules.base import AbstractIntentRule
from app.domain.intents.rules.pack import AbstractRulePack


class CustomRulePack(AbstractRulePack):
    """Container for dynamically registered custom enterprise rules."""

    def __init__(self, pack_name: str = "CustomRulePack", rules: List[AbstractIntentRule] = None):
        self._pack_name = pack_name
        self._rules = list(rules or [])

    @property
    def pack_name(self) -> str:
        return self._pack_name

    @property
    def description(self) -> str:
        return f"Dynamic custom enterprise rule pack '{self._pack_name}'"

    def add_rule(self, rule: AbstractIntentRule) -> None:
        self._rules.append(rule)

    def get_rules(self) -> List[AbstractIntentRule]:
        return list(self._rules)
