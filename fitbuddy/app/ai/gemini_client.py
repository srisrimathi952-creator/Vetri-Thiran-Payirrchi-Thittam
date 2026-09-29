from functools import lru_cache

from app.config import settings


@lru_cache
def get_gemini_client():
    """
    Lazily create the Google GenAI client.

    Lazy loading is intentional:
    - tests can run without Gemini installed/configured
    - demo mode can run without an API key
    - importing the application doesn't immediately contact Google
    """

    if not settings.gemini_api_key:
        return None

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "The google-genai package is not installed. "
            "Run: pip install -r requirements.txt"
        ) from exc

    return genai.Client(
        api_key=settings.gemini_api_key
    )


def get_structured_config(response_schema):
    """
    Configuration used for Gemini structured JSON responses.
    """

    try:
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "The google-genai package is not installed."
        ) from exc

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
        temperature=0.7,
    )