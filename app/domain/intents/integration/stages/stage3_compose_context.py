"""
HunterOS Engage V1 - Stage 3: Compose Context
Phase 2.3.5: Intent Intelligence – Intent Integration Layer
"""

from __future__ import annotations

import logging
import time

from app.domain.intents.integration.context import IntentIntegrationPipelineContext
from app.domain.intents.integration.registry import IntentContextRegistry, default_context_registry

logger = logging.getLogger(__name__)


class Stage3_ComposeContext:
    """Resolves active CompositionProfile from registry and prepares base context structure."""

    def __init__(self, registry: Optional[IntentContextRegistry] = None) -> None:
        self.registry = registry or default_context_registry

    def execute(self, ctx: IntentIntegrationPipelineContext) -> None:
        start = time.perf_counter()

        profile = self.registry.get_profile(ctx.profile_type)
        ctx.active_profile = profile

        logger.debug("Stage 3 Active Profile: %s (%s)", profile.profile_name, profile.profile_type)
        ctx.stage_timings_ms["stage3_compose_context_ms"] = (time.perf_counter() - start) * 1000
