"""
HunterOS Engage V1 - Tests for Insight Execution Context & State Machine
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

import uuid
import pytest

from app.domain.conversations.insight.context import (
    ConversationInsightContext,
    InsightPipelineState,
)


def test_context_initial_state():
    ctx = ConversationInsightContext(conversation_id="conv-1")
    assert ctx.current_state == InsightPipelineState.INITIALIZED
    assert ctx.is_valid is True
    assert len(ctx.warnings) == 0
    assert len(ctx.validation_errors) == 0


def test_context_state_transitions():
    ctx = ConversationInsightContext(conversation_id="conv-1")
    ctx.transition_to(InsightPipelineState.LOADING)
    assert ctx.current_state == InsightPipelineState.LOADING

    ctx.transition_to(InsightPipelineState.DETECTING_RISKS)
    assert ctx.current_state == InsightPipelineState.DETECTING_RISKS

    ctx.transition_to(InsightPipelineState.COMPLETED)
    assert ctx.current_state == InsightPipelineState.COMPLETED


def test_context_timing_and_diagnostics():
    ctx = ConversationInsightContext(conversation_id="conv-1")
    ctx.record_stage_execution("LoadArtifactsStage", 4.2)
    ctx.record_stage_execution("DetectRisksStage", 8.5)

    assert "LoadArtifactsStage" in ctx.stages_executed
    assert "DetectRisksStage" in ctx.stages_executed
    assert ctx.stage_timings_ms["LoadArtifactsStage"] == 4.2
    assert ctx.stage_timings_ms["DetectRisksStage"] == 8.5


def test_context_validation_errors():
    ctx = ConversationInsightContext(conversation_id="conv-1")
    assert ctx.is_valid is True

    ctx.add_warning("Minor warning")
    assert len(ctx.warnings) == 1
    assert ctx.is_valid is True

    ctx.add_validation_error("Fatal boundary violation")
    assert len(ctx.validation_errors) == 1
    assert ctx.is_valid is False
