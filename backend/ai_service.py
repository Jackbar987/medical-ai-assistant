"""
ai_service.py - the one place that talks to the AI provider (Anthropic's Claude).

Every feature sends its AI requests through ask(). Keeping all provider code
in this file means:
- the API key is read in exactly one place,
- errors are turned into friendly messages in one place,
- switching AI providers only means rewriting this file. (We started with
  OpenAI and switched to Claude by changing only this file, the settings
  and requirements.txt.)

How an API request works: our server sends Anthropic a message over HTTPS
that includes our secret API key (to prove who we are and who pays), the
model's name, the instructions, and the conversation. Anthropic sends back
the model's reply. The browser never sees the key, because only this
server-side Python code talks to Anthropic.

Settings (read from environment variables, see .env.example):
    ANTHROPIC_API_KEY   required: the secret key from platform.claude.com
    ANTHROPIC_MODEL     optional: which Claude model to use
"""

import logging
import os

import anthropic

# Messages logged here appear in the terminal locally, and in Vercel's logs
# when deployed. We only ever log the TYPE of problem, never what users wrote.
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-5-5"

# The longest reply allowed, in tokens (about 3 characters each). This also
# leaves room for any thinking the model does before answering.
MAX_TOKENS = 4000

PLACEHOLDER_KEY = "your-anthropic-api-key-here"


class AIServiceError(Exception):
    """
    Raised when the AI can't answer. Its message is written for the person
    using the app, so the route can show it as it is. It never contains
    technical details or secrets.
    """


_client = None  # created on first use, then reused


def _get_client():
    """Create the Anthropic client the first time it is needed."""
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        # Treat the placeholder from .env.example the same as a missing key.
        if not api_key or api_key == PLACEHOLDER_KEY:
            logger.error("ANTHROPIC_API_KEY is not set. Add it to .env (locally) or to Vercel's environment variables.")
            raise AIServiceError("The assistant isn't set up yet. Please try again later.")
        # timeout: give up after 60 seconds. max_retries: try once more on a
        # temporary network problem.
        _client = anthropic.Anthropic(api_key=api_key, timeout=60, max_retries=1)
    return _client


def ask(instructions, messages):
    """
    Send instructions and a conversation to Claude and return its reply text.

    instructions: the rules for the AI (see backend/safety.py). Anthropic
        calls this the "system" prompt.
    messages: a list like [{"role": "user", "content": "..."}, ...].
        It must start with a "user" message, which our chat always does.

    Raises AIServiceError with a user-friendly message if anything goes wrong.
    """
    client = _get_client()
    model = os.getenv("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL

    try:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=instructions,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        )
    except anthropic.AuthenticationError:
        logger.error("Anthropic rejected the API key. Check ANTHROPIC_API_KEY.")
        raise AIServiceError("The assistant isn't set up correctly. Please try again later.")
    except anthropic.RateLimitError:
        # This includes reaching the spend limit set in the Claude Console.
        logger.warning("Anthropic rate or spend limit reached.")
        raise AIServiceError("The assistant is busy or has reached its usage limit. Wait a few minutes and try again.")
    except anthropic.APITimeoutError:
        logger.warning("Anthropic request timed out.")
        raise AIServiceError("The assistant took too long to answer. Try sending your message again.")
    except anthropic.APIConnectionError:
        logger.warning("Could not connect to Anthropic.")
        raise AIServiceError("The assistant couldn't be reached. Try again in a moment.")
    except anthropic.OverloadedError:
        # Anthropic's servers are temporarily too busy (status 529).
        logger.warning("Anthropic is overloaded.")
        raise AIServiceError("The assistant is busy right now. Try again in a moment.")
    except anthropic.APIError as error:
        # Any other problem: a wrong model name, an overloaded service, and so on.
        logger.error("Anthropic error: %s (status %s)", type(error).__name__, getattr(error, "status_code", None))
        raise AIServiceError("Something went wrong with the assistant. Try again in a moment.")

    # A reply is made of "content blocks". We keep only the text blocks;
    # other kinds (such as the model's thinking) are not shown to users.
    text = "".join(block.text for block in response.content if block.type == "text").strip()

    if not text:
        logger.warning("Anthropic returned no text (stop reason: %s).", response.stop_reason)
        raise AIServiceError("The assistant couldn't finish its answer. Try asking again, or shorten your message.")

    if response.stop_reason == "max_tokens":
        # The reply was cut off. Rare with our length rules, but say so.
        text += "\n\n(This reply was cut short. Ask a narrower question for a complete answer.)"

    return text
