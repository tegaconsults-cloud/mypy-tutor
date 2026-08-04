import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_api_key = os.getenv("GROQ_API_KEY")
if not _api_key:
    raise ValueError(
        "GROQ_API_KEY is not set. Please add it to your .env file or environment."
    )

_client = Groq(api_key=_api_key, timeout=28.0)  # 28s hard timeout — prevents hang on Render

# Model routing:
#   FAST  — llama-3.1-8b-instant   : quiz eval, exercise gen, course steps, general Q&A
#           (low latency, deterministic, short output)
#   SMART — llama-3.3-70b-versatile: concept explanations, debug, codegen
#           (highest quality, used where depth and reasoning matter)
_FAST_MODEL  = "llama-3.1-8b-instant"
_SMART_MODEL = "llama-3.3-70b-versatile"

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
