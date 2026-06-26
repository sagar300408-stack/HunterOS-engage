"""
OpenAI integration client — Chat Completions API wrapper.

Captures full response metadata for every call:
  model, tokens, latency, estimated cost, finish_reason, prompt_version.

These are stored in ai_metadata and power the Phase 5 analytics dashboard.
"""

import time
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """Return (or lazily create) the shared AsyncOpenAI client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
        logger.info("openai_client_initialized", model=settings.openai_model)
    return _client


def load_system_prompt(version: Optional[str] = None) -> str:
    """
    Load the system prompt from app/prompts/{version}.txt.

    Falls back to a safe default if the file is missing.
    Switching prompts requires only changing ACTIVE_PROMPT_VERSION in .env.
    """
    settings = get_settings()
    version = version or settings.active_prompt_version

    # Resolve path relative to this file's location
    prompts_dir = Path(__file__).parent.parent.parent / "prompts"
    prompt_path = prompts_dir / f"{version}.txt"

    if not prompt_path.exists():
        logger.warning(
            "system_prompt_not_found",
            version=version,
            path=str(prompt_path),
            fallback="using_inline_default",
        )
        return (
            "You are HunterOS Engage, a professional AI customer engagement assistant. "
            "Be helpful, concise, and accurate."
        )

    content = prompt_path.read_text(encoding="utf-8").strip()
    logger.debug("system_prompt_loaded", version=version, char_count=len(content))
    return content


# ── Token cost table (update when OpenAI pricing changes) ─────────────────────
_COST_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4o":          {"prompt": 0.005,  "completion": 0.015},
    "gpt-4o-mini":     {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4-turbo":     {"prompt": 0.010,  "completion": 0.030},
    "gpt-3.5-turbo":   {"prompt": 0.0005, "completion": 0.0015},
}
_DEFAULT_COST = {"prompt": 0.005, "completion": 0.015}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate the cost of an API call in USD."""
    rates = _COST_PER_1K_TOKENS.get(model, _DEFAULT_COST)
    return round(
        (prompt_tokens / 1000) * rates["prompt"]
        + (completion_tokens / 1000) * rates["completion"],
        6,
    )


async def get_ai_response(
    conversation_history: list[dict],
    user_message: str,
    prompt_version: Optional[str] = None,
) -> dict:
    """
    Call the OpenAI Chat Completions API and return a structured result dict.

    Returns:
        {
            "content":              str,
            "model":                str,
            "prompt_tokens":        int,
            "completion_tokens":    int,
            "total_tokens":         int,
            "latency_ms":           int,
            "estimated_cost_usd":   float,
            "finish_reason":        str,
            "prompt_version":       str,
        }
    """
    settings = get_settings()
    client = get_openai_client()
    version = prompt_version or settings.active_prompt_version
    system_prompt = load_system_prompt(version)

    # Build the full message array: system + history + new user message
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    logger.info(
        "ai_processing_started",
        model=settings.openai_model,
        prompt_version=version,
        history_turns=len(conversation_history),
        user_message_preview=user_message[:80],
    )

    start_time = time.monotonic()

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )

    latency_ms = int((time.monotonic() - start_time) * 1000)
    choice = response.choices[0]
    usage = response.usage
    estimated_cost = _estimate_cost(
        response.model, usage.prompt_tokens, usage.completion_tokens
    )

    result = {
        "content":            choice.message.content.strip(),
        "model":              response.model,
        "prompt_tokens":      usage.prompt_tokens,
        "completion_tokens":  usage.completion_tokens,
        "total_tokens":       usage.total_tokens,
        "latency_ms":         latency_ms,
        "estimated_cost_usd": estimated_cost,
        "finish_reason":      choice.finish_reason,
        "prompt_version":     version,
    }

    logger.info(
        "ai_processing_completed",
        model=result["model"],
        total_tokens=result["total_tokens"],
        latency_ms=result["latency_ms"],
        finish_reason=result["finish_reason"],
        estimated_cost_usd=result["estimated_cost_usd"],
        prompt_version=result["prompt_version"],
    )

    return result
