"""
Multi-provider LLM client for MyPy Tutor — Sir. Tega AI engine.

Provider cascade (zero-downtime fallback):
  Provider 1 — Groq          (primary, fastest — LPU inference)
  Provider 2 — Google Gemini (secondary — free tier, very capable)
  Provider 3 — OpenRouter    (tertiary  — routes to many models)

Within each provider, multiple models are tried before moving to the next.
The user NEVER sees an error unless all three providers are down simultaneously.

Env vars required (set in Render → Environment):
  GROQ_API_KEY          — from console.groq.com
  GEMINI_API_KEY        — from aistudio.google.com (free)
  OPENROUTER_API_KEY    — from openrouter.ai (free tier available)
"""

import os
import logging
import time

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Provider 1 — Groq
# ─────────────────────────────────────────────────────────────────────────────

_groq_client     = None
_groq_client_key = None

def _get_groq_client():
    global _groq_client, _groq_client_key
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    if _groq_client is None or key != _groq_client_key:
        from groq import Groq
        _groq_client     = Groq(api_key=key, timeout=45.0)
        _groq_client_key = key
        logger.info("Groq client initialised")
    return _groq_client


_GROQ_FAST_MODEL  = "openai/gpt-oss-20b"
_GROQ_SMART_MODEL = "openai/gpt-oss-120b"

_GROQ_MODEL_SEQUENCE = [
    "openai/gpt-oss-120b",                          # most capable Groq model
    "openai/gpt-oss-20b",                           # fastest Groq model
    "meta-llama/llama-4-scout-17b-16e-instruct",    # Llama 4 Scout
    "meta-llama/llama-4-maverick-17b-128e-instruct",# Llama 4 Maverick
    "llama-3.3-70b-versatile",                      # legacy — may still work
    "llama-3.1-8b-instant",                         # legacy last resort
]


def _call_groq(system_prompt: str, messages: list[dict],
               intent: str, temperature: float) -> str:
    client = _get_groq_client()
    primary = _GROQ_SMART_MODEL if intent in _SMART_INTENTS else _GROQ_FAST_MODEL
    sequence = [primary] + [m for m in _GROQ_MODEL_SEQUENCE if m != primary]

    for model in sequence:
        max_tokens = _INTENT_MAX_TOKENS.get(intent, 1500)
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                messages=[{"role": "system", "content": system_prompt}, *messages],
            )
            content = resp.choices[0].message.content
            if content and content.strip():
                if model != primary:
                    logger.info("Groq fallback success: model=%s intent=%s", model, intent)
                return content
            raise ValueError("Empty response")
        except Exception as exc:
            err = str(exc).lower()
            logger.warning("Groq model=%s failed: %s", model, str(exc)[:100])
            # If it's a rate limit, wait briefly before next model
            if any(k in err for k in ("429", "ratelimit", "rate_limit", "overloaded")):
                time.sleep(2)
            # If model doesn't exist, skip immediately
            if any(k in err for k in ("model_not_found", "model not found",
                                       "does not exist", "deprecated", "404")):
                continue
            # Other errors: try next model
            continue

    raise RuntimeError("All Groq models exhausted")


# ─────────────────────────────────────────────────────────────────────────────
# Provider 2 — Google Gemini
# ─────────────────────────────────────────────────────────────────────────────

_gemini_client     = None
_gemini_client_key = None

def _get_gemini_client():
    global _gemini_client, _gemini_client_key
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    if _gemini_client is None or key != _gemini_client_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            _gemini_client     = genai
            _gemini_client_key = key
            logger.info("Gemini client initialised")
        except ImportError:
            raise RuntimeError(
                "google-generativeai not installed. Add it to requirements.txt"
            )
    return _gemini_client


# Gemini model preference order — free tier models first
_GEMINI_MODELS = [
    "gemini-1.5-flash",          # free tier, fast, 1M context
    "gemini-1.5-flash-8b",       # free tier, smallest/fastest
    "gemini-1.5-pro",            # free tier with limits, most capable
    "gemini-2.0-flash-exp",      # experimental but available free
]


def _call_gemini(system_prompt: str, messages: list[dict],
                 intent: str, temperature: float) -> str:
    import google.generativeai as genai
    _get_gemini_client()

    # Build the combined prompt — Gemini uses a different message format
    # Prepend the system prompt as the first user turn for compatibility
    combined_messages = []
    for m in messages:
        combined_messages.append({
            "role":  "user" if m["role"] == "user" else "model",
            "parts": [m["content"]],
        })

    # Gemini GenerationConfig
    max_tokens = _INTENT_MAX_TOKENS.get(intent, 1500)

    for model_name in _GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                ),
            )
            response = model.generate_content(combined_messages)
            content  = response.text
            if content and content.strip():
                if model_name != _GEMINI_MODELS[0]:
                    logger.info("Gemini fallback success: model=%s intent=%s", model_name, intent)
                return content
            raise ValueError("Empty response from Gemini")
        except Exception as exc:
            err = str(exc).lower()
            logger.warning("Gemini model=%s failed: %s", model_name, str(exc)[:100])
            if any(k in err for k in ("429", "quota", "resource_exhausted", "rate")):
                time.sleep(3)
            continue

    raise RuntimeError("All Gemini models exhausted")


# ─────────────────────────────────────────────────────────────────────────────
# Provider 3 — OpenRouter
# ─────────────────────────────────────────────────────────────────────────────

# OpenRouter uses the OpenAI-compatible API at https://openrouter.ai/api/v1
# Many free models available — we try capable free ones first.
_OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",     # powerful, free
    "meta-llama/llama-3.1-8b-instruct:free",      # fast, free
    "google/gemma-2-9b-it:free",                  # Google, free
    "mistralai/mistral-7b-instruct:free",         # Mistral, free
    "qwen/qwen-2.5-72b-instruct:free",            # Qwen 72B, free
    "deepseek/deepseek-r1:free",                  # DeepSeek, free
]


def _call_openrouter(system_prompt: str, messages: list[dict],
                     intent: str, temperature: float) -> str:
    import httpx

    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    max_tokens = _INTENT_MAX_TOKENS.get(intent, 1500)
    headers = {
        "Authorization":  f"Bearer {key}",
        "Content-Type":   "application/json",
        "HTTP-Referer":   "https://mypytutor.com.ng",
        "X-Title":        "MyPy Tutor — Sir. Tega",
    }

    for model in _OPENROUTER_MODELS:
        payload = {
            "model":       model,
            "temperature": temperature,
            "max_tokens":  max_tokens,
            "messages":    [
                {"role": "system", "content": system_prompt},
                *messages,
            ],
        }
        try:
            r = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=40,
            )
            if r.status_code == 429:
                logger.warning("OpenRouter rate limit on %s, sleeping 3s", model)
                time.sleep(3)
                continue
            if r.status_code >= 400:
                logger.warning("OpenRouter HTTP %s for %s: %s", r.status_code, model, r.text[:100])
                continue
            data    = r.json()
            content = data["choices"][0]["message"]["content"]
            if content and content.strip():
                if model != _OPENROUTER_MODELS[0]:
                    logger.info("OpenRouter fallback success: model=%s intent=%s", model, intent)
                return content
            raise ValueError("Empty response from OpenRouter")
        except Exception as exc:
            logger.warning("OpenRouter model=%s failed: %s", model, str(exc)[:100])
            continue

    raise RuntimeError("All OpenRouter models exhausted")


# ─────────────────────────────────────────────────────────────────────────────
# Shared constants
# ─────────────────────────────────────────────────────────────────────────────

_SMART_INTENTS = {"concept", "debug", "codegen", "general"}

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


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point — cascades through all 3 providers
# ─────────────────────────────────────────────────────────────────────────────

def get_completion(
    system_prompt: str,
    messages: list[dict],
    model: str = "",
    temperature: float = 0.3,
    intent: str = "",
) -> str:
    """
    Call the best available LLM with full 3-provider cascade.

    Provider order:
      1. Groq        — fastest (LPU hardware), primary
      2. Gemini      — Google free tier, highly capable
      3. OpenRouter  — many free models, last line of defence

    Within each provider, multiple models are tried before moving on.
    The function only raises if ALL providers fail — which should be
    essentially impossible with three independent API keys.

    Voice (TTS) does NOT call this — it uses the browser Web Speech API.
    """
    providers = []

    # Only include providers whose API keys are configured
    if os.getenv("GROQ_API_KEY"):
        providers.append(("Groq",        _call_groq))
    if os.getenv("GEMINI_API_KEY"):
        providers.append(("Gemini",       _call_gemini))
    if os.getenv("OPENROUTER_API_KEY"):
        providers.append(("OpenRouter",   _call_openrouter))

    if not providers:
        raise RuntimeError(
            "No LLM API keys configured. Set at least one of: "
            "GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY in Render → Environment."
        )

    last_exc: Exception | None = None

    for provider_name, provider_fn in providers:
        try:
            content = provider_fn(system_prompt, messages, intent, temperature)
            if content and content.strip():
                return content
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Provider %s failed completely: %s — trying next provider",
                provider_name, str(exc)[:120]
            )
            continue

    # All providers failed
    error_summary = str(last_exc)[:200] if last_exc else "unknown error"
    logger.error("All LLM providers failed. Last error: %s", error_summary)
    raise RuntimeError(
        "Sir. Tega is temporarily unavailable — all AI providers are busy. "
        "Please try again in a moment."
    )


# Backwards-compatible alias for any code that imports _get_client directly
def _get_client():
    return _get_groq_client()
