import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_api_key = os.getenv("GROQ_API_KEY")
if not _api_key:
    raise ValueError(
        "GROQ_API_KEY is not set. Please add it to your .env file or environment."
    )

_client = Groq(api_key=_api_key, timeout=30.0)  # 30s hard timeout

# Model routing — updated August 2026 after Groq deprecated llama-3.x models:
#   FAST  — openai/gpt-oss-20b   : quiz eval, exercise gen, course steps, general Q&A
#            (replaces llama-3.1-8b-instant — low latency, ~1000 tok/s on LPU)
#   SMART — openai/gpt-oss-120b  : concept explanations, debug, codegen
#            (replaces llama-3.3-70b-versatile — flagship quality on Groq LPU)
#
# Note: llama-3.1-8b-instant and llama-3.3-70b-versatile were shut down by Groq
# on August 16, 2026. These are the official Groq-recommended replacements.
_FAST_MODEL  = "openai/gpt-oss-20b"
_SMART_MODEL = "openai/gpt-oss-120b"

# Intents that genuinely need deep reasoning — use SMART model
# "course" removed: course steps are structured content, not open-ended reasoning
# Using 8b-instant for course steps reduces latency from ~6s to ~1-2s
_SMART_INTENTS = {"concept", "debug", "codegen", "general"}

# Token caps per model — balanced for quality vs. latency on Render free tier
_MAX_TOKENS: dict[str, int] = {
    _SMART_MODEL: 3000,   # concept/debug/codegen — reduced from 4096 (saves ~1s)
    _FAST_MODEL:  1500,   # quiz/exercise/course — reduced from 2048 (saves ~0.5s)
}


def get_completion(
    system_prompt: str,
    messages: list[dict],
    model: str = "",          # "" = auto-select by intent
    temperature: float = 0.3,
    intent: str = "",         # hint for auto model selection
) -> str:
    """
    Calls Groq Chat Completions and returns the assistant message content.
    Auto-selects model and max_tokens based on intent when model="" (default).
    """
    if not model:
        model = _SMART_MODEL if intent in _SMART_INTENTS else _FAST_MODEL

    max_tokens = _MAX_TOKENS.get(model, 2048)

    response = _client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[{"role": "system", "content": system_prompt}, *messages],
    )
    return response.choices[0].message.content
