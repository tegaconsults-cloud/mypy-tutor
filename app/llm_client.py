"""
Groq LLM client for MyPy Tutor — Sir. Tega AI engine.

Models (current as of August 2026 — llama-3.x deprecated June 17, 2026):
  FAST  — openai/gpt-oss-20b   : ~1000 tok/s on Groq LPU, quiz/exercise/course steps
  SMART — openai/gpt-oss-120b  : ~500 tok/s, concept explanations/debug/codegen

Fallback chain (ensures zero silent failures):
  1. Primary model (SMART or FAST based on intent)
  2. Swap: if SMART fails → try FAST; if FAST fails → try SMART
  3. Last resort: llama-3.1-8b-instant (if still available) or any available model
"""

import os
import logging
import time

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client — lazy init so missing GROQ_API_KEY doesn't crash the whole app
# ---------------------------------------------------------------------------
_client     = None
_client_key = None   # track which key the client was built with


def _get_client():
    """Return a Groq client, (re-)initialised if the API key changed."""
    global _client, _client_key
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Go to Render → mypy-tutor → Environment "
            "and add your Groq API key."
        )
    if _client is None or key != _client_key:
        from groq import Groq
        _client     = Groq(api_key=key, timeout=25.0)
        _client_key = key
        logger.info("Groq client initialised")
    return _client


# ---------------------------------------------------------------------------
# Model routing
# ---------------------------------------------------------------------------

# Primary models — current Groq production models (August 2026)
_FAST_MODEL  = "openai/gpt-oss-20b"     # ~1000 tok/s — quiz, exercise, course, general
_SMART_MODEL = "openai/gpt-oss-120b"    # ~500 tok/s  — concept, debug, codegen

# Fallback models tried in order if primary fails
# (ordered from most capable to most available)
_FALLBACK_MODELS = [
    "openai/gpt-oss-20b",           # cross-fallback from smart → fast
    "openai/gpt-oss-120b",          # cross-fallback from fast → smart
    "llama-3.3-70b-versatile",      # legacy — may still work on some accounts
    "llama-3.1-8b-instant",         # legacy — fastest fallback
    "llama3-70b-8192",              # older model still on some Groq tiers
    "llama3-8b-8192",               # last resort
]

# Intents that need deep reasoning — use SMART model
_SMART_INTENTS = {"concept", "debug", "codegen", "general"}

# Token caps per intent
_INTENT_MAX_TOKENS: dict[str, int] = {
    "quiz":       512,
    "quiz_eval":  512,
    "exercise":   800,
    "course":     1500,
    "concept":    2048,
    "debug":      2048,
    "codegen":    2048,
    "general":    1500,
    "ambiguous":  800,
}

_MODEL_MAX_TOKENS: dict[str, int] = {
    _SMART_MODEL:              2048,
    _FAST_MODEL:               1500,
    "llama-3.3-70b-versatile": 2048,
    "llama-3.1-8b-instant":    1500,
    "llama3-70b-8192":         2048,
    "llama3-8b-8192":          1500,
}


def _get_max_tokens(model: str, intent: str) -> int:
    if intent in _INTENT_MAX_TOKENS:
        return _INTENT_MAX_TOKENS[intent]
    return _MODEL_MAX_TOKENS.get(model, 1500)


def _is_transient(exc: Exception) -> bool:
    """True if the error is likely temporary and worth retrying."""
    msg  = str(exc).lower()
    name = type(exc).__name__.lower()
    return any(k in msg or k in name for k in (
        "ratelimit", "rate_limit", "rate limit",
        "timeout", "timed out",
        "503", "502", "429",
        "serviceunavailable", "service_unavailable",
        "connection", "network",
        "overloaded",
    ))


def _is_model_error(exc: Exception) -> bool:
    """True if the model itself is unavailable/invalid — try a different model."""
    msg = str(exc).lower()
    return any(k in msg for k in (
        "model_not_found", "model not found",
        "does not exist", "not found", "404",
        "deprecated", "no longer available",
        "invalid model",
    ))


# ---------------------------------------------------------------------------
# Core completion function with full fallback chain
# ---------------------------------------------------------------------------

def get_completion(
    system_prompt: str,
    messages: list[dict],
    model: str = "",
    temperature: float = 0.3,
    intent: str = "",
) -> str:
    """
    Call Groq Chat Completions with automatic model fallback.

    Fallback chain:
      1. Primary model (SMART or FAST based on intent)
      2. If transient error: retry primary up to 2× with backoff
      3. If model error: try cross-fallback (smart→fast, fast→smart)
      4. If still failing: walk through _FALLBACK_MODELS list
      5. If all models fail: raise with clear error message

    Voice (TTS) does NOT call this function — it uses the browser's
    Web Speech API directly. This function is only for chat/quiz/courses.
    """
    # Determine primary model
    primary = model if model else (_SMART_MODEL if intent in _SMART_INTENTS else _FAST_MODEL)

    # Build the fallback sequence: primary first, then others (deduplicated)
    fallback_sequence = [primary]
    for m in _FALLBACK_MODELS:
        if m not in fallback_sequence:
            fallback_sequence.append(m)

    last_exc: Exception | None = None

    for attempt_idx, current_model in enumerate(fallback_sequence):
        max_retries = 2 if attempt_idx == 0 else 1  # retry primary more, others once
        for retry in range(max_retries):
            try:
                client     = _get_client()
                max_tokens = _get_max_tokens(current_model, intent)

                response = client.chat.completions.create(
                    model=current_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                    messages=[{"role": "system", "content": system_prompt}, *messages],
                )
                content = response.choices[0].message.content
                if not content or not content.strip():
                    raise ValueError("Empty response from model")

                if attempt_idx > 0 or retry > 0:
                    logger.info(
                        "LLM success on fallback: model=%s attempt=%d retry=%d intent=%s",
                        current_model, attempt_idx, retry, intent
                    )
                return content

            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "LLM attempt failed: model=%s retry=%d/%d intent=%s error=%s",
                    current_model, retry + 1, max_retries, intent, str(exc)[:120]
                )

                if _is_model_error(exc):
                    logger.warning("Model unavailable (%s) — skipping to next fallback", current_model)
                    break  # skip remaining retries for this model, try next

                if _is_transient(exc) and retry < max_retries - 1:
                    wait = (retry + 1) * 1.5
                    logger.info("Transient error — waiting %.1fs before retry", wait)
                    time.sleep(wait)
                    continue

                if attempt_idx == 0:
                    break  # first model failed non-transiently — try fallbacks

    # All models failed
    error_summary = str(last_exc)[:200] if last_exc else "unknown error"
    logger.error("All LLM models failed. Last error: %s", error_summary)
    raise RuntimeError(
        f"Sir. Tega is temporarily unavailable. All models tried. Last error: {error_summary}"
    )
