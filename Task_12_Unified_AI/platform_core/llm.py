import os

from .models import PlatformError


def enabled():
    backend = os.getenv("AI_BACKEND", "local").strip().lower()

    if backend not in {"local", "groq"}:
        raise PlatformError(
            "Set AI_BACKEND to local or groq in your .env file."
        )

    return backend == "groq"


def complete(system: str, question: str) -> str:
    if not enabled():
        raise PlatformError("Enable Groq using AI_BACKEND=groq.")

    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not api_key or api_key.startswith("your_"):
        raise PlatformError(
            "Missing Groq API key. Set GROQ_API_KEY in your .env file."
        )

    try:
        from groq import (
            Groq,
            AuthenticationError,
            RateLimitError,
            APIConnectionError,
            APIStatusError,
        )
    except ImportError:
        raise PlatformError(
            "Groq package is missing. Run: python -m pip install groq"
        ) from None

    try:
        with Groq(
            api_key=api_key,
            timeout=45.0,
            max_retries=1,
        ) as client:
            result = client.chat.completions.create(
                model=os.getenv(
                    "GROQ_MODEL", "openai/gpt-oss-120b"
                ).strip(),
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": question},
                ],
                temperature=0,
                max_completion_tokens=4096,
            )

        if not result.choices:
            raise PlatformError("Groq returned no answer. Please retry.")

        choice = result.choices[0]

        if choice.finish_reason == "length":
            raise PlatformError(
                "The model response was incomplete. Try a narrower question."
            )

        text = (choice.message.content or "").strip()

        if not text:
            raise PlatformError("Groq returned an empty answer. Please retry.")

        return text

    except AuthenticationError:
        raise PlatformError(
            "Groq authentication failed. Check GROQ_API_KEY."
        ) from None
    except RateLimitError:
        raise PlatformError(
            "Groq rate limit reached. Wait briefly and retry."
        ) from None
    except APIConnectionError:
        raise PlatformError(
            "Cannot connect to Groq. Check your internet connection."
        ) from None
    except APIStatusError as exc:
        raise PlatformError(
            f"Groq request failed (HTTP {exc.status_code}). "
            "Check your model name, account access, and request limits."
        ) from None