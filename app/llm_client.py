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
    _SMART_MODEL: 2048,   # concept/debug/codegen — trimmed from 3000 (~1s latency saving)
    _FAST_MODEL:  1500,   # quiz/exercise/course steps — balanced for quality vs speed
}

# Course steps need more tokens than quiz — override per intent
_INTENT_MAX_TOKENS: dict[str, int] = {
    "quiz":       512,    # question + 4 options + answer + brief explanation
    "quiz_eval":  512,    # correct/false + explanation + encouragement
    "exercise":   800,    # exercise description + starter code
    "course":     1500,   # full lesson content
}

def _get_max_tokens(model: str, intent: str) -> int:
    """Return token cap: intent-specific override first, then model default."""
    if intent in _INTENT_MAX_TOKENS:
        return _INTENT_MAX_TOKENS[intent]
    return _MAX_TOKENS.get(model, 1500)


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
    Uses intent-specific token caps so quiz/eval calls return fast (~512 tok)
    while concept/debug/codegen calls get full quality (~2048 tok).
    stream=False is explicit — ensures we never accidentally block on a stream.
    """
    if not model:
        model = _SMART_MODEL if intent in _SMART_INTENTS else _FAST_MODEL

    max_tokens = _get_max_tokens(model, intent)

    response = _client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False,          # explicit — prevents accidental streaming block
        messages=[{"role": "system", "content": system_prompt}, *messages],
    )
    return response.choices[0].message.content
