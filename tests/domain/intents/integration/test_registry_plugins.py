"""
Unit Tests for Intent Context Registry & Plugin Extensions (Phase 2.3.5)
"""

import pytest

from app.domain.intents.integration.models import (
    CompositionProfileType,
    IntentIntelligenceContext,
)
from app.domain.intents.integration.profiles.base import CompositionProfile
from app.domain.intents.integration.registry import (
    IntentContextRegistry,
    IntentIntelligencePlugin,
)


class CustomTestProfile(CompositionProfile):
    @property
    def profile_name(self) -> str:
        return "custom_test_profile"

    @property
    def profile_type(self) -> CompositionProfileType:
        return CompositionProfileType.CUSTOM

    def apply(self, context: IntentIntelligenceContext, options: dict) -> None:
        context.diagnostics.rules_applied.append("CustomTestRuleApplied")


class CustomPlugin(IntentIntelligencePlugin):
    @property
    def plugin_name(self) -> str:
        return "analytics_plugin_v1"

    @property
    def version(self) -> str:
        return "1.0.0"

    def register(self, registry: IntentContextRegistry) -> None:
        registry.register_profile(CustomTestProfile())


def test_registry_and_plugins():
    registry = IntentContextRegistry()
    assert len(registry.list_profiles()) == 10

    plugin = CustomPlugin()
    registry.register_plugin(plugin)

    assert len(registry.list_plugins()) == 1
    assert registry.list_plugins()[0]["name"] == "analytics_plugin_v1"

    retrieved = registry.get_profile("custom_test_profile")
    assert retrieved.profile_name == "custom_test_profile"
