"""
HunterOS Engage V1 - Stage 4: Apply Profile
Phase 2.3.5: Intent Intelligence – Intent Integration Layer
"""

from __future__ import annotations

import logging
import time

from app.domain.intents.integration.context import IntentIntegrationPipelineContext

logger = logging.getLogger(__name__)


class Stage4_ApplyProfile:
    """Executes the declarative composition profile against the pipeline context."""

    def execute(self, ctx: IntentIntegrationPipelineContext) -> None:
        start = time.perf_counter()

        if not ctx.active_profile:
            logger.warning("No active profile found in Stage 4. Skipping profile execution.")
            return

        logger.debug("Stage 4 Applying profile %s", ctx.active_profile.profile_name)
        ctx.stage_timings_ms["stage4_apply_profile_ms"] = (time.perf_counter() - start) * 1000
