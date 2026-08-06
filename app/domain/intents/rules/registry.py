"""
HunterOS Engage V1 - Intent Rule Pack Registry
Thread-safe registry managing modular industry rule packs.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from app.domain.intents.rules.base import AbstractIntentRule
from app.domain.intents.rules.pack import AbstractRulePack
from app.domain.intents.rules.packs.core import CoreRulePack
from app.domain.intents.rules.packs.real_estate import RealEstateRulePack


class IntentRulePackRegistry:
    """Thread-safe registry for modular intent rule packs."""

    def __init__(self, register_defaults: bool = True):
        self._lock = threading.RLock()
        self._packs: Dict[str, AbstractRulePack] = {}

        if register_defaults:
            self.register_pack(CoreRulePack())
            self.register_pack(RealEstateRulePack())

    def register_pack(self, pack: AbstractRulePack) -> None:
        """Register a modular rule pack."""
        with self._lock:
            self._packs[pack.pack_name] = pack

    def unregister_pack(self, pack_name: str) -> None:
        """Unregister a rule pack by name."""
        with self._lock:
            self._packs.pop(pack_name, None)

    def get_pack(self, pack_name: str) -> Optional[AbstractRulePack]:
        """Retrieve a rule pack by name."""
        with self._lock:
            return self._packs.get(pack_name)

    def list_packs(self) -> List[AbstractRulePack]:
        """List all registered rule packs."""
        with self._lock:
            return list(self._packs.values())

    def get_all_rules(self) -> List[AbstractIntentRule]:
        """Aggregate and return all rules across all registered packs."""
        with self._lock:
            all_rules: List[AbstractIntentRule] = []
            for pack in self._packs.values():
                all_rules.extend(pack.get_rules())
            return all_rules


# Default singleton instance
default_rule_pack_registry = IntentRulePackRegistry(register_defaults=True)
