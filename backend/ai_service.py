"""
ai_service.py - the one place that talks to the AI provider (OpenAI).

Every feature sends its AI requests through ask(). Keeping all OpenAI code
in this file means:
- the API key is read in exactly one place,
- errors are turned into friendly messages in one place,
- switching AI providers later only means rewriting this file.

How an API request works: our server sends OpenAI a message over HTTPS that
includes our secret API key (to prove who we are and who pays), the model's
name, the instructions, and the conversation. OpenAI sends back the model's
reply. The browser never sees the key, because only this server-side Python
code talks to OpenAI.

Settings (read from environment variables, see .env.example):
    OPENAI_API_KEY           required: the secret key from platform.openai.com
    OPENAI_MODEL             optional: which model to use
    OPENAI_REASONING_EFFORT  optional: how long the model "thinks" first
"""

import logging
import os

import openai

# Messages logged here appear in the terminal locally, and in Vercel's logs
# when deployed. We only ever log the TYPE of problem, never what users wrote.
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-6.1-sol"
DEFAULT_REASONING_EFFORT = "low"  # faster replies; plenty for explanations

# Room for the model's hidden "thinking" plus the visible answer.
MAX_OUTPUT_TOKENS = 2500


class AIServiceError(Exception):
    """
    Raised when the AI can't answer. Its message is written for the person
    using the app, so the route can show it as it is. It never contains
    technical details or secrets.
    """


_client = None  # created on first use, then reused


def _get_client():
    """Create the OpenAI client the first time it is needed."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        # Treat the placeholder from .env.example the same as a missing key.
        if not api_key or api_key == "your-openai-api-key-here":
            logger.error("OPENAI_API_KEY is not set. Add it to .env (locally) or to Vercel's environment variables.")
            raise AIServiceError("The assistant isn't set up yet. Please try again later.")
        # timeout: give up after 60 seconds. max_retries: try once more on a
        # temporary network problem.
        _client = openai.OpenAI(api_key=api_key, timeout=60, max_retries=1)
    return _client


def ask(instructions, messages):
    """
    Send instructions and a conversation to the AI and return its reply text.

    instructions: the rules for the AI (see backend/safety.py).
    messages: a list like [{"role": "user", "content": "..."}, ...].

    Raises AIServiceError with a user-friendly message if anything goes wrong.
    """
    client = _get_client()
    model = os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_MODEL
    effort = os.getenv("OPENAI_REASONING_EFFORT", DEFAULT_REASONING_EFFORT).strip()

    # Only include the "reasoning" setting if one is chosen. Leave
    # OPENAI_REASONING_EFFORT empty in .env for models that don't support it.
    extra_settings = {}
    if effort:
        extra_settings["reasoning"] = {"effort": effort}

    try:
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=[{"role": m["role"], "content": m["content"]} for m in messages],
            max_output_tokens=MAX_OUTPUT_TOKENS,
            # Ask OpenAI not to keep this conversation after answering, since
            # it may contain health information.
            store=False,
            **extra_settings,
        )
    except openai.AuthenticationError:
        logger.error("OpenAI rejected the API key. Check OPENAI_API_KEY.")
        raise AIServiceError("The assistant isn't set up correctly. Please try again later.")
    except openai.RateLimitError as error:
        # This includes reaching the spending limit set on the OpenAI account.
        logger.warning("OpenAI rate or spend limit reached: %s", getattr(error, "code", None))
        raise AIServiceError("The assistant is busy or has reached its usage limit. Wait a few minutes and try again.")
    except openai.APITimeoutError:
        logger.warning("OpenAI request timed out.")
        raise AIServiceError("The assistant took too long to answer. Try sending your message again.")
    except openai.APIConnectionError:
        logger.warning("Could not connect to OpenAI.")
        raise AIServiceError("The assistant couldn't be reached. Try again in a moment.")
    except openai.APIError as error:
        # Any other problem: a wrong model name, an outage, and so on.
        logger.error("OpenAI error: %s (status %s)", type(error).__name__, getattr(error, "status_code", None))
        raise AIServiceError("Something went wrong with the assistant. Try again in a moment.")

    text = (response.output_text or "").strip()
    if not text:
        logger.warning("OpenAI returned no text (status: %s).", getattr(response, "status", None))
        raise AIServiceError("The assistant couldn't finish its answer. Try asking again, or shorten your message.")

    return text
