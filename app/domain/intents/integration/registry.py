"""
HunterOS Engage V1 - Intent Context Registry & Plugin Framework
Phase 2.3.5: Intent Intelligence – Intent Integration Layer

Central registry for Composition Profiles, Assemblers, Validators, Exporters,
and Industry Extension Plugins.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union
import threading

from app.domain.intents.integration.models import CompositionProfileType
from app.domain.intents.integration.profiles.base import CompositionProfile
from app.domain.intents.integration.profiles.minimal import MinimalProfile
from app.domain.intents.integration.profiles.classification import ClassificationProfile
from app.domain.intents.integration.profiles.evolution import EvolutionProfile
from app.domain.intents.integration.profiles.resolution import ResolutionProfile
from app.domain.intents.integration.profiles.full import FullProfile
from app.domain.intents.integration.profiles.executive import ExecutiveProfile
from app.domain.intents.integration.profiles.sales import SalesProfile
from app.domain.intents.integration.profiles.operations import OperationsProfile
from app.domain.intents.integration.profiles.audit import AuditProfile
from app.domain.intents.integration.profiles.custom import CustomProfile

logger = logging.getLogger(__name__)


class IntentIntelligencePlugin:
    """
    Modular plugin bundle for extending the Intent Intelligence Platform.
    Allows industry verticals (SaaS, RealEstate, Healthcare, Ecommerce) to contribute
    custom composition profiles, validators, and export transformers.
    """

    def __init__(
        self,
        plugin_name: str = "custom_plugin",
        plugin_version: str = "1.0.0",
        description: str = "",
        profiles: Optional[List[CompositionProfile]] = None,
        validators: Optional[List[Any]] = None,
        exporters: Optional[Dict[str, Callable[..., Any]]] = None,
    ) -> None:
        self._plugin_name = plugin_name
        self._plugin_version = plugin_version
        self.description = description
        self.profiles = profiles or []
        self.validators = validators or []
        self.exporters = exporters or {}

    @property
    def plugin_name(self) -> str:
        return getattr(self, "_plugin_name", "custom_plugin")

    @property
    def version(self) -> str:
        return getattr(self, "_plugin_version", "1.0.0")

    @property
    def plugin_version(self) -> str:
        return self.version

    def register(self, registry: Any) -> None:
        """Subclasses can override to register profiles/validators with registry."""
        pass


class IntentContextRegistry:
    """
    Thread-safe central registry managing all Intent Intelligence platform extensions.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._profiles: Dict[str, CompositionProfile] = {}
        self._plugins: Dict[str, IntentIntelligencePlugin] = {}
        self._validators: List[Any] = []
        self._exporters: Dict[str, Callable[..., Any]] = {}

        # Register default builtin profiles
        self._register_default_profiles()

    def _register_default_profiles(self) -> None:
        builtins = [
            MinimalProfile(),
            ClassificationProfile(),
            EvolutionProfile(),
            ResolutionProfile(),
            FullProfile(),
            ExecutiveProfile(),
            SalesProfile(),
            OperationsProfile(),
            AuditProfile(),
            CustomProfile(),
        ]
        for p in builtins:
            self.register_profile(p)

    def register_profile(self, profile: CompositionProfile) -> None:
        with self._lock:
            key_name = profile.profile_name.upper()
            key_type = profile.profile_type.value.upper() if hasattr(profile.profile_type, "value") else str(profile.profile_type).upper()
            self._profiles[key_name] = profile
            self._profiles[key_type] = profile
            logger.debug("Registered Intent Composition Profile: %s (%s)", profile.profile_name, key_type)

    def get_profile(self, profile_key: Union[str, CompositionProfileType]) -> CompositionProfile:
        with self._lock:
            key = profile_key.value.upper() if isinstance(profile_key, CompositionProfileType) else str(profile_key).upper()
            if key in self._profiles:
                return self._profiles[key]
            # Fallback to FullProfile
            logger.warning("Composition profile '%s' not found in registry. Falling back to FullProfile.", profile_key)
            return self._profiles.get("FULL", FullProfile())

    def list_profiles(self) -> List[Dict[str, Any]]:
        with self._lock:
            unique_profiles = set(self._profiles.values())
            return [
                {
                    "profile_name": p.profile_name,
                    "profile_type": p.profile_type.value if hasattr(p.profile_type, "value") else str(p.profile_type),
                    "required_modules": p.required_modules,
                    "description": p.description,
                }
                for p in unique_profiles
            ]

    def register_plugin(self, plugin: IntentIntelligencePlugin) -> None:
        with self._lock:
            p_name = plugin.plugin_name
            self._plugins[p_name] = plugin
            if hasattr(plugin, "register") and callable(plugin.register):
                plugin.register(self)
            for prof in getattr(plugin, "profiles", []):
                self.register_profile(prof)
            for val in getattr(plugin, "validators", []):
                self._validators.append(val)
            for exp_name, exp_fn in getattr(plugin, "exporters", {}).items():
                self._exporters[exp_name] = exp_fn
            logger.info("Registered Intent Intelligence Plugin: %s v%s", p_name, getattr(plugin, "version", "1.0.0"))

    def list_plugins(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "name": p.plugin_name,
                    "plugin_name": p.plugin_name,
                    "version": getattr(p, "version", getattr(p, "plugin_version", "1.0.0")),
                    "plugin_version": getattr(p, "version", getattr(p, "plugin_version", "1.0.0")),
                    "description": getattr(p, "description", ""),
                    "profiles_count": len(getattr(p, "profiles", [])),
                }
                for p in self._plugins.values()
            ]

    def register_exporter(self, name: str, exporter_fn: Callable[..., Any]) -> None:
        with self._lock:
            self._exporters[name.upper()] = exporter_fn

    def get_exporter(self, name: str) -> Optional[Callable[..., Any]]:
        with self._lock:
            return self._exporters.get(name.upper())


# Global singleton instance
default_context_registry = IntentContextRegistry()
