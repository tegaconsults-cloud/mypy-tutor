import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_api_key = os.getenv("GROQ_API_KEY")
if not _api_key:
    raise ValueError(
        "GROQ_API_KEY is not set. Please add it to your .env file or environment."
    )

_client = Groq(api_key=_api_key)


def get_completion(
    system_prompt: str,
    messages: list[dict],
    model: str = "llama-3.1-8b-instant",
    temperature: float = 0.3,
) -> str:
    """
    Calls Groq Chat Completions and returns the assistant message content.

    Args:
        system_prompt: The system instruction string.
        messages: List of prior conversation messages in OpenAI format.
        model: The Groq model to use.
        temperature: Sampling temperature (0.0–2.0).

    Returns:
        The assistant's response as a plain string.
    """
    response = _client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{"role": "system", "content": system_prompt}, *messages],
    )
    return response.choices[0].message.content
