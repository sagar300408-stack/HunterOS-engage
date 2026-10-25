"""
Tests for AI Provider Selection and Dynamic Contextual Responses (DEF-01 / DEF-02).
"""
import pytest
import os
from unittest.mock import patch, MagicMock

from app.integrations.openai.provider import get_ai_provider, OpenAIProvider, SimulatedAIProvider


def test_get_ai_provider_returns_simulated_when_explicitly_set():
    with patch.dict(os.environ, {"AI_PROVIDER": "simulated", "OPENAI_API_KEY": "sk-realtestkey"}):
        provider = get_ai_provider()
        assert isinstance(provider, SimulatedAIProvider)


def test_get_ai_provider_returns_openai_when_real_key_present():
    with patch.dict(os.environ, {"AI_PROVIDER": "openai", "OPENAI_API_KEY": "sk-realtestkey1234567890"}):
        provider = get_ai_provider()
        assert isinstance(provider, OpenAIProvider)


def test_get_ai_provider_returns_simulated_with_mock_key():
    mock_settings = MagicMock()
    mock_settings.app_env = "testing"
    mock_settings.openai_api_key = "mock-test-key"
    mock_settings.is_production = False

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("AI_PROVIDER", None)
        with patch("app.integrations.openai.provider.get_settings", return_value=mock_settings):
            provider = get_ai_provider()
            assert isinstance(provider, SimulatedAIProvider)


@pytest.mark.asyncio
async def test_simulated_provider_contextual_responses():
    provider = SimulatedAIProvider()

    # 1. Appointment booking intent
    booking_resp = await provider.get_ai_response(
        conversation_history=[],
        user_message="I would like to schedule a demo consultation tomorrow at 2 PM",
    )
    assert any(k in booking_resp["content"].lower() for k in ["schedule", "demo", "appointment", "visit"])
    assert booking_resp["finish_reason"] == "stop"

    # 2. Pricing intent
    pricing_resp = await provider.get_ai_response(
        conversation_history=[],
        user_message="How much does your subscription cost? What is the pricing?",
    )
    assert any(k in pricing_resp["content"].lower() for k in ["pricing", "cost", "budget", "$400,000", "properties"])

    # 3. Stop / Opt-out intent
    stop_resp = await provider.get_ai_response(
        conversation_history=[],
        user_message="STOP UNSUBSCRIBE please",
    )
    assert any(k in stop_resp["content"].lower() for k in ["unsubscribed", "opted out", "stop"])

    # 4. Greeting intent
    hello_resp = await provider.get_ai_response(
        conversation_history=[],
        user_message="Hello there!",
    )
    assert any(k in hello_resp["content"].lower() for k in ["hunteros", "originyx", "assist", "help", "hello"])
