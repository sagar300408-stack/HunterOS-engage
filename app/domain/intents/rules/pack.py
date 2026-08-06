"""
HunterOS Engage V1 - Abstract Rule Pack Base
Modular groupings of intent rules by domain vertical (Core, Real Estate, Healthcare, Manufacturing, Custom).
"""

from __future__ import annotations

import abc
from typing import List

from app.domain.intents.rules.base import AbstractIntentRule


class AbstractRulePack(abc.ABC):
    """Modular bundle of intent detection rules for an industry or core capability."""

    @property
    @abc.abstractmethod
    def pack_name(self) -> str:
        """Name of the rule pack (e.g. 'CoreRulePack', 'RealEstateRulePack')."""
        pass

    @property
    def pack_version(self) -> str:
        """Semantic version of the rule pack."""
        return "1.0.0"

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Description of the vertical or intent coverage."""
        pass

    @abc.abstractmethod
    def get_rules(self) -> List[AbstractIntentRule]:
        """Returns the list of instantiated rule instances in this pack."""
        pass
