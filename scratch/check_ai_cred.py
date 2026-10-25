import sys, os
sys.path.insert(0, os.getcwd())

from app.config import get_settings
from app.integrations.openai.provider import get_ai_provider, OpenAIProvider, SimulatedAIProvider

settings = get_settings()
raw_key = settings.openai_api_key or ""
ai_provider_env = os.environ.get("AI_PROVIDER", "")

has_key = bool(raw_key)
is_placeholder = (
    not has_key
    or raw_key.startswith("mock-")
    or raw_key in ("sk-test", "your-openai-api-key-here", "placeholder")
    or len(raw_key) < 20
)
is_real_format = has_key and (raw_key.startswith("sk-proj-") or raw_key.startswith("sk-")) and len(raw_key) >= 30 and not is_placeholder

print(f"[AI CREDENTIAL CHECK] Key present: {has_key}")
print(f"[AI CREDENTIAL CHECK] Key length: {len(raw_key)}")
print(f"[AI CREDENTIAL CHECK] Key starts with sk-: {raw_key.startswith('sk-')}")
print(f"[AI CREDENTIAL CHECK] Key is placeholder/mock: {is_placeholder}")
print(f"[AI CREDENTIAL CHECK] Key format appears real: {is_real_format}")
print(f"[AI CREDENTIAL CHECK] AI_PROVIDER env var: '{ai_provider_env}'")

provider = get_ai_provider()
print(f"[AI CREDENTIAL CHECK] Active Provider Class: {provider.__class__.__name__}")
