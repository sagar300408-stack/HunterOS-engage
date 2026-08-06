"""
HunterOS Engage V1 - Classification Rule Registry
Thread-safe registry for versioned classification rule packs.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from app.domain.intents.classification.rules.base import (
    AbstractClassificationRule,
    AbstractClassificationRulePack,
)
from app.domain.intents.classification.rules.packs.core import CoreClassificationRulePack
from app.domain.intents.classification.rules.packs.healthcare import (
    HealthcareClassificationRulePack,
)
from app.domain.intents.classification.rules.packs.real_estate import (
    RealEstateClassificationRulePack,
)


class ClassificationRuleRegistry:
    """
    Manages pluggable, versioned classification rule packs.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._packs: Dict[str, AbstractClassificationRulePack] = {}
        self._initialize_defaults()

    def register_pack(self, pack: AbstractClassificationRulePack) -> None:
        """Register or update a rule pack."""
        with self._lock:
            self._packs[pack.pack_name] = pack

    def unregister_pack(self, pack_name: str) -> Optional[AbstractClassificationRulePack]:
        """Remove a rule pack by name."""
        with self._lock:
            return self._packs.pop(pack_name, None)

    def get_pack(self, pack_name: str) -> Optional[AbstractClassificationRulePack]:
        """Look up a rule pack."""
        with self._lock:
            return self._packs.get(pack_name)

    def list_packs(self) -> List[AbstractClassificationRulePack]:
        """List all registered rule packs."""
        with self._lock:
            return list(self._packs.values())

    def list_all_rules(self, active_pack_names: Optional[List[str]] = None) -> List[AbstractClassificationRule]:
        """List all rules across active packs (or all packs if none specified)."""
        with self._lock:
            rules: List[AbstractClassificationRule] = []
            for name, pack in self._packs.items():
                if active_pack_names is None or name in active_pack_names:
                    rules.extend(pack.get_rules())
            return rules

    def _initialize_defaults(self) -> None:
        """Seed default rule packs."""
        self.register_pack(CoreClassificationRulePack(version="1.0.0"))
        self.register_pack(RealEstateClassificationRulePack(version="1.0.0"))
        self.register_pack(HealthcareClassificationRulePack(version="1.0.0"))


default_classification_rule_registry = ClassificationRuleRegistry()
