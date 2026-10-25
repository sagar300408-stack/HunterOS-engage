import sys, os
sys.path.insert(0, os.getcwd())

print("Step 1: starting", flush=True)
import asyncio
from unittest.mock import patch
print("Step 2: importing provider", flush=True)
from app.integrations.openai.provider import get_ai_provider, OpenAIProvider, SimulatedAIProvider
print("Step 3: provider imported", flush=True)

def test_1():
    print("Step 4: test_1 starting", flush=True)
    with patch.dict(os.environ, {"AI_PROVIDER": "simulated", "OPENAI_API_KEY": "sk-realtestkey"}):
        provider = get_ai_provider()
        assert isinstance(provider, SimulatedAIProvider)
    print("Test 1 passed", flush=True)

def test_2():
    print("Step 5: test_2 starting", flush=True)
    with patch.dict(os.environ, {"AI_PROVIDER": "openai", "OPENAI_API_KEY": "sk-realtestkey1234567890"}):
        provider = get_ai_provider()
        assert isinstance(provider, OpenAIProvider)
    print("Test 2 passed", flush=True)

async def test_3():
    print("Step 6: test_3 starting", flush=True)
    provider = SimulatedAIProvider()
    print("Step 7: provider created, calling get_ai_response", flush=True)
    booking_resp = await provider.get_ai_response([], "I want to schedule an appointment for a viewing")
    print("Step 8: got booking response:", booking_resp["content"], flush=True)

if __name__ == "__main__":
    test_1()
    test_2()
    asyncio.run(test_3())
    print("Done!", flush=True)
