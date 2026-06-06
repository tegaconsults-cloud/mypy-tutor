"""
FastAPI application entry point for the AI Python Tutor.
Wires together the classifier, prompt builder, LLM client, and formatter.
"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.classifier import classify_intent
from app.formatter import format_response
from app.llm_client import get_completion
from app.models import ChatRequest, ChatResponse
from app.prompts import build_system_prompt
from app.topics import get_topics

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

try:
    # Importing llm_client already validates the API key (raises ValueError if
    # GROQ_API_KEY is missing).  We re-import here only to surface the error
    # at startup with a clear log message rather than silently at first request.
    import app.llm_client  # noqa: F401 — side-effect: key validation
except ValueError as exc:
    logger.error("Startup error: %s", exc)
    raise

app = FastAPI(title="MyPy Tutor", version="1.0.0")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Accept a user message (with optional history), classify intent, build a
    system prompt, call the LLM, and return a structured ChatResponse.
    """
    # 1. Validate non-empty message
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # 2. Classify intent
    intent = classify_intent(request.message)

    # 3. Build system prompt
    system_prompt = build_system_prompt(intent)

    # 4. Assemble message list for the LLM
    messages = [{"role": m.role, "content": m.content} for m in request.history]
    messages.append({"role": "user", "content": request.message})

    # 5. Call the LLM (handle OpenAI errors)
    try:
        content = get_completion(system_prompt, messages)
    except Exception as exc:
        exc_type = type(exc).__name__.lower()
        # Rate-limit and timeout errors → 503
        if any(keyword in exc_type for keyword in ("ratelimit", "timeout", "serviceunavailable")):
            logger.warning("LLM unavailable: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="LLM unavailable, please retry",
            )
        # All other OpenAI / network errors → 502
        logger.error("LLM error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))

    # 6. Format the response
    response_dict = format_response(content, intent)

    # 7. Return typed response
    return ChatResponse(**response_dict)


@app.get("/topics")
async def topics() -> dict:
    """Return the list of supported Python topics."""
    return {"topics": get_topics()}


@app.get("/health")
async def health() -> dict:
    """Simple health-check endpoint."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Custom error handlers
# ---------------------------------------------------------------------------


@app.exception_handler(400)
async def bad_request_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": "Bad request"})


@app.exception_handler(502)
async def bad_gateway_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=502, content={"error": "Bad gateway"})


@app.exception_handler(503)
async def service_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503, content={"error": "LLM unavailable, please retry"}
    )


# ---------------------------------------------------------------------------
# Static files — must be mounted LAST so API routes take precedence
# ---------------------------------------------------------------------------

app.mount("/", StaticFiles(directory="static", html=True), name="static")
