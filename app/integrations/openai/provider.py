from abc import ABC, abstractmethod
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
        if simulation_state.openai_status == "offline":
            raise Exception("OpenAI API is offline (Simulated)")
        elif simulation_state.openai_status == "timeout":
            await asyncio.sleep(10.0)
            raise Exception("OpenAI API request timed out (Simulated)")

        settings = get_settings()
        version = prompt_version or settings.active_prompt_version
        
        # Generate realistic mock real estate reply
        import random
        # If there's a specific mock reply registered for this scenario turn, use it
        if hasattr(simulation_state, "next_mock_reply") and simulation_state.next_mock_reply:
            reply = simulation_state.next_mock_reply
            simulation_state.next_mock_reply = None
        else:
            mock_replies = [
                "Hello! Thanks for reaching out. Yes, we have several beautiful 2-bedroom apartments in that location starting at $400,000. Would you like to schedule a site visit?",
                "That sounds like a great budget. We have a couple of premium villas in your preferred area that match your timeline. Let me know if you would like to see photos.",
                "Thank you for confirming your budget increase. I have updated your profile. We have some exclusive listings that are now within your range.",
                "Excellent! I have scheduled a site visit for this weekend. A sales agent will contact you shortly to confirm the exact time.",
                "I understand your requirements. We can negotiate the down payment terms with the developer. Let me see what we can do.",
                "Great news! Your booking is confirmed. I am preparing the digital contract now.",
                "Thank you for your interest. Please let us know if you decide to restart your search in the future."
            ]
            reply = random.choice(mock_replies)

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
    if settings.enable_developer_tools:
        from app.developer_tools.service import simulation_state
        # If key is dummy/default, or mock_ai is specifically active
        if settings.openai_api_key.startswith("dummy") or settings.openai_api_key == "change-me" or simulation_state.mock_ai:
            return SimulatedAIProvider()
    return OpenAIProvider()
