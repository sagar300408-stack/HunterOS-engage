from abc import ABC, abstractmethod
import os
from typing import Optional
from app.config import get_settings
from app.integrations.openai.client import get_ai_response as real_get_ai_response

class AIProvider(ABC):
    @abstractmethod
    async def get_ai_response(
        self,
        conversation_history: list[dict],
        user_message: str,
        prompt_version: Optional[str] = None,
    ) -> dict:
        pass

class OpenAIProvider(AIProvider):
    async def get_ai_response(
        self,
        conversation_history: list[dict],
        user_message: str,
        prompt_version: Optional[str] = None,
    ) -> dict:
        return await real_get_ai_response(conversation_history, user_message, prompt_version)

class SimulatedAIProvider(AIProvider):
    async def get_ai_response(
        self,
        conversation_history: list[dict],
        user_message: str,
        prompt_version: Optional[str] = None,
    ) -> dict:
        import asyncio
        from app.developer_tools.service import simulation_state
        
        # Check simulation status
        if getattr(simulation_state, "network_delay", 0) > 0:
            await asyncio.sleep(simulation_state.network_delay)

        if getattr(simulation_state, "error_rate", 0) > 0:
            import random
            if random.random() < simulation_state.error_rate:
                raise Exception("Simulated OpenAI API Error (Rate Limit/500)")

        if getattr(simulation_state, "timeout", False):
            raise Exception("OpenAI API request timed out (Simulated)")

        settings = get_settings()
        version = prompt_version or settings.active_prompt_version
        
        # 1. If explicit next_mock_reply is queued in simulation_state, prioritize it
        if hasattr(simulation_state, "next_mock_reply") and simulation_state.next_mock_reply:
            reply = simulation_state.next_mock_reply
            simulation_state.next_mock_reply = None
        else:
            # 2. Context-aware deterministic reply based on user intent
            msg_lower = (user_message or "").lower()
            if any(k in msg_lower for k in ["book", "appointment", "schedule", "visit", "meeting"]):
                reply = "I would be happy to help schedule an appointment. What date and time works best for you?"
            elif any(k in msg_lower for k in ["price", "cost", "budget", "pricing"]):
                reply = "Our properties in that area start at $400,000. Could you share your preferred budget range so I can find matching options?"
            elif any(k in msg_lower for k in ["bedroom", "bhk", "villa", "apartment", "location"]):
                reply = "We have several premium listings matching those specifications. Would you like to review their floor plans or schedule a viewing?"
            elif any(k in msg_lower for k in ["stop", "unsubscribe", "cancel follow", "opt out"]):
                reply = "You have been unsubscribed from further automated messages. Please let us know if you need any further assistance."
            elif any(k in msg_lower for k in ["hello", "hi", "hey"]):
                reply = "Hello! I am your HunterOS assistant. How can I help you find your ideal property today?"
            else:
                reply = "Thank you for reaching out. Could you share more details about your requirements so I can assist you better?"

        return {
            "content": reply,
            "model": settings.openai_model,
            "prompt_tokens": 150,
            "completion_tokens": 50,
            "total_tokens": 200,
            "latency_ms": 150,
            "estimated_cost_usd": 0.001,
            "finish_reason": "stop",
            "prompt_version": version,
        }

def get_ai_provider() -> AIProvider:
    settings = get_settings()
    provider_override = os.environ.get("AI_PROVIDER", "").lower()
    if provider_override == "simulated":
        return SimulatedAIProvider()
    elif provider_override == "openai":
        return OpenAIProvider()

    # In testing environment or if API key is a dummy test key, use deterministic SimulatedAIProvider
    if (
        settings.app_env == "testing"
        or not settings.openai_api_key
        or settings.openai_api_key.startswith("mock-")
        or settings.openai_api_key == "sk-test"
    ):
        return SimulatedAIProvider()

    # In production, require valid non-mock API key
    if settings.is_production:
        if not settings.openai_api_key or settings.openai_api_key.startswith("mock-"):
            raise RuntimeError("OPENAI_API_KEY is not configured for production environment.")
        return OpenAIProvider()

    # In development:
    if settings.openai_api_key and not settings.openai_api_key.startswith("mock-"):
        return OpenAIProvider()

    return SimulatedAIProvider()
