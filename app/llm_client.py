"""
Multi-provider LLM client for MyPy Tutor — Sir. Tega AI engine.

Provider cascade (zero-downtime — users NEVER see an error):
  Provider 1 — Groq          (primary — fastest, LPU hardware)
  Provider 2 — Google Gemini (secondary — free tier, very capable)
  Provider 3 — OpenRouter    (fallback — routes to many free models)

Each provider tries multiple models internally before moving to the next.
On transient errors (rate-limit, timeout, 503) the provider retries with
exponential backoff before giving up and moving on.

Env vars (set in Render → Environment):
  GROQ_API_KEY          — console.groq.com
  GEMINI_API_KEY        — aistudio.google.com  (free)
  OPENROUTER_API_KEY    — openrouter.ai         (free tier)
"""

import os
import logging
import time

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Shared intent→token caps ───────────────────────────────────────────────
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

# ── Error classification helpers ───────────────────────────────────────────
def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("429", "rate_limit", "ratelimit", "rate limit",
                                   "overloaded", "capacity", "quota", "resource_exhausted"))

def _is_model_gone(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("model_not_found", "model not found", "does not exist",
                                   "deprecated", "no longer available", "invalid model")) \
           or ("404" in msg and "model" in msg)

def _is_transient(exc: Exception) -> bool:
    msg  = str(exc).lower()
    name = type(exc).__name__.lower()
    return any(k in msg or k in name for k in
               ("timeout", "timed out", "503", "502", "connection",
                "network", "eof", "reset", "broken pipe", "sslerror"))


# ═══════════════════════════════════════════════════════════════════════════
# Provider 1 — Groq  (PRIMARY)
# ═══════════════════════════════════════════════════════════════════════════

_groq_client = None
_groq_key    = None

def _get_groq():
    global _groq_client, _groq_key
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    if _groq_client is None or key != _groq_key:
        from groq import Groq
        _groq_client = Groq(api_key=key, timeout=50.0)
        _groq_key    = key
        logger.info("Groq client initialised")
    return _groq_client


# Ordered by quality/availability — best first
_GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

def _call_groq(system: str, messages: list[dict], intent: str, temp: float) -> str:
    client  = _get_groq()
    primary = _GROQ_MODELS[0] if intent in _SMART_INTENTS else _GROQ_MODELS[1]
    # Always try primary first, then rest
    seq     = [primary] + [m for m in _GROQ_MODELS if m != primary]
    tokens  = _INTENT_MAX_TOKENS.get(intent, 1500)

    for model in seq:
        retries = 3 if model == primary else 1
        for attempt in range(retries):
            try:
                resp = client.chat.completions.create(
                    model=model, temperature=temp,
                    max_tokens=tokens, stream=False,
                    messages=[{"role": "system", "content": system}, *messages],
                )
                text = (resp.choices[0].message.content or "").strip()
                if text:
                    if model != primary or attempt > 0:
                        logger.info("Groq OK: model=%s attempt=%d intent=%s", model, attempt, intent)
                    return text
                raise ValueError("Empty Groq response")
            except Exception as exc:
                logger.warning("Groq model=%s attempt=%d/%d: %s", model, attempt+1, retries, str(exc)[:100])
                if _is_model_gone(exc):
                    break   # skip remaining retries for this model
                if _is_rate_limit(exc) and attempt < retries - 1:
                    wait = 2 ** attempt * 2   # 2s, 4s
                    logger.info("Groq rate-limited — waiting %ds", wait)
                    time.sleep(wait)
                    continue
                if _is_transient(exc) and attempt < retries - 1:
                    time.sleep(1.5)
                    continue
                break   # non-retryable error — try next model

    raise RuntimeError("Groq: all models exhausted")


# ═══════════════════════════════════════════════════════════════════════════
# Provider 2 — Google Gemini  (SECONDARY)
# ═══════════════════════════════════════════════════════════════════════════

_gemini_mod  = None
_gemini_key  = None

def _get_gemini():
    global _gemini_mod, _gemini_key
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    if _gemini_mod is None or key != _gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            _gemini_mod = genai
            _gemini_key = key
            logger.info("Gemini client initialised")
        except ImportError:
            raise RuntimeError("google-generativeai not installed")
    return _gemini_mod

# Free-tier models ordered best→fastest
_GEMINI_MODELS = [
    "gemini-2.0-flash",           # latest flash — fast & capable
    "gemini-1.5-flash",           # stable free tier
    "gemini-1.5-flash-8b",        # smallest/fastest
    "gemini-1.5-pro",             # most capable (stricter rate limits)
]

def _call_gemini(system: str, messages: list[dict], intent: str, temp: float) -> str:
    genai  = _get_gemini()
    tokens = _INTENT_MAX_TOKENS.get(intent, 1500)

    # Convert to Gemini's message format
    gm = [{"role": "user" if m["role"] == "user" else "model",
            "parts": [m["content"]]} for m in messages]

    for model_name in _GEMINI_MODELS:
        retries = 2 if model_name == _GEMINI_MODELS[0] else 1
        for attempt in range(retries):
            try:
                model  = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system,
                    generation_config=genai.GenerationConfig(
                        max_output_tokens=tokens, temperature=temp),
                )
                resp = model.generate_content(gm)
                text = (resp.text or "").strip()
                if text:
                    if model_name != _GEMINI_MODELS[0] or attempt > 0:
                        logger.info("Gemini OK: model=%s attempt=%d", model_name, attempt)
                    return text
                raise ValueError("Empty Gemini response")
            except Exception as exc:
                logger.warning("Gemini model=%s attempt=%d: %s", model_name, attempt+1, str(exc)[:100])
                if _is_rate_limit(exc) and attempt < retries - 1:
                    time.sleep(3)
                    continue
                break

    raise RuntimeError("Gemini: all models exhausted")


# ═══════════════════════════════════════════════════════════════════════════
# Provider 3 — OpenRouter  (FALLBACK)
# ═══════════════════════════════════════════════════════════════════════════

# Free models — ordered by capability
_OR_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "deepseek/deepseek-r1:free",
]

def _call_openrouter(system: str, messages: list[dict], intent: str, temp: float) -> str:
    import httpx
    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    tokens  = _INTENT_MAX_TOKENS.get(intent, 1500)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://mypytutor.com.ng",
        "X-Title":       "MyPy Tutor — Sir. Tega",
    }

    for model in _OR_MODELS:
        retries = 2 if model == _OR_MODELS[0] else 1
        for attempt in range(retries):
            try:
                r = httpx.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json={"model": model, "temperature": temp, "max_tokens": tokens,
                          "messages": [{"role": "system", "content": system}, *messages]},
                    timeout=45,
                )
                if r.status_code == 429:
                    if attempt < retries - 1:
                        time.sleep(3)
                        continue
                    break
                if r.status_code >= 400:
                    logger.warning("OpenRouter HTTP %s for %s: %s", r.status_code, model, r.text[:80])
                    break
                text = (r.json()["choices"][0]["message"]["content"] or "").strip()
                if text:
                    if model != _OR_MODELS[0] or attempt > 0:
                        logger.info("OpenRouter OK: model=%s attempt=%d", model, attempt)
                    return text
                raise ValueError("Empty OpenRouter response")
            except Exception as exc:
                logger.warning("OpenRouter model=%s attempt=%d: %s", model, attempt+1, str(exc)[:100])
                if _is_rate_limit(exc) and attempt < retries - 1:
                    time.sleep(3)
                    continue
                break

    raise RuntimeError("OpenRouter: all models exhausted")


# ═══════════════════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════════════════

def get_completion(
    system_prompt: str,
    messages: list[dict],
    model: str = "",
    temperature: float = 0.3,
    intent: str = "",
) -> str:
    """
    Call the best available LLM. Provider order: Groq → Gemini → OpenRouter.
    Only raises RuntimeError if ALL configured providers fail — essentially
    impossible with 3 independent keys.

    Voice/TTS does NOT call this — it uses the browser Web Speech API.
    """
    providers: list[tuple[str, object]] = []

    if os.getenv("GROQ_API_KEY"):
        providers.append(("Groq",       _call_groq))
    if os.getenv("GEMINI_API_KEY"):
        providers.append(("Gemini",     _call_gemini))
    if os.getenv("OPENROUTER_API_KEY"):
        providers.append(("OpenRouter", _call_openrouter))

    if not providers:
        raise RuntimeError(
            "No LLM API keys configured. Add GROQ_API_KEY (and optionally "
            "GEMINI_API_KEY / OPENROUTER_API_KEY) to Render → Environment."
        )

    last_exc: Exception | None = None

    for provider_name, provider_fn in providers:
        try:
            text = provider_fn(system_prompt, messages, intent, temperature)  # type: ignore[operator]
            if text and text.strip():
                return text
        except Exception as exc:
            last_exc = exc
            logger.warning("Provider %s failed: %s — next provider", provider_name, str(exc)[:120])
            continue

    # All providers exhausted
    err = str(last_exc)[:200] if last_exc else "no providers configured"
    logger.error("All LLM providers failed: %s", err)
    raise RuntimeError(
        "Sir. Tega is briefly unavailable — please try again in a moment."
    )


# Backwards-compat alias
def _get_client():
    return _get_groq()
