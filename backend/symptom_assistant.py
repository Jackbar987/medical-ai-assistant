"""
symptom_assistant.py - logic for the Symptom Information Assistant.

The browser sends the whole conversation so far as a list of messages:

    [
        {"role": "user", "content": "I've had a headache for three days."},
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "It's worse in the morning."},
    ]

The server keeps no memory between requests. This is deliberate: nothing
about the user's health is stored, and it works on serverless hosting like
Vercel, where each request may be handled by a fresh copy of the app.

How a reply is made (Phase 3):
1. safety.check_message() looks at the newest message for signs of an
   emergency or crisis. If it finds one, we answer with fixed emergency
   guidance and don't ask the AI at all.
2. Otherwise the conversation goes to the AI through ai_service.ask(),
   together with the symptom instructions from safety.py.
"""

from backend import ai_service, safety

# Limits that protect the server (and, later, our AI bill) from huge requests.
MAX_USER_MESSAGE_LENGTH = 2000       # characters in one message from the user
MAX_ASSISTANT_MESSAGE_LENGTH = 10000  # characters in one earlier reply
MAX_MESSAGES = 30                     # messages in one conversation


def validate_conversation(messages):
    """
    Check that the conversation sent by the browser is usable.

    Returns None if everything is fine, or a short error message that can be
    shown to the user. We never trust data from the browser: anyone can send
    any request to our server, not only through our page.
    """
    if not isinstance(messages, list) or len(messages) == 0:
        return "Type a message before sending."

    if len(messages) > MAX_MESSAGES:
        return "This conversation has reached its length limit. Clear it to start a new one."

    for message in messages:
        if (
            not isinstance(message, dict)
            or message.get("role") not in ("user", "assistant")
            or not isinstance(message.get("content"), str)
        ):
            return "The conversation could not be read. Clear it and try again."

        if message["role"] == "user":
            limit = MAX_USER_MESSAGE_LENGTH
        else:
            limit = MAX_ASSISTANT_MESSAGE_LENGTH

        if len(message["content"]) > limit:
            return f"Messages can be up to {MAX_USER_MESSAGE_LENGTH} characters. Shorten your message and try again."

    latest = messages[-1]
    if latest["role"] != "user":
        return "The conversation could not be read. Clear it and try again."

    if latest["content"].strip() == "":
        return "Type a message before sending."

    return None


def check_for_urgent(messages):
    """
    Check the newest message for an emergency or crisis.

    Returns a reply dictionary with fixed guidance, or None if nothing was
    found. This runs before the AI and before the rate limit, so this
    guidance is always shown immediately, for free.
    """
    kind = safety.check_message(messages[-1]["content"])
    if kind is None:
        return None
    return {"reply": safety.urgent_reply(kind), "urgent": True}


def get_reply(messages):
    """
    Ask the AI for a reply to the conversation.

    Returns {"reply": "...", "urgent": False}. If the AI can't answer,
    ai_service.ask() raises ai_service.AIServiceError, which app.py turns into
    an error message for the user.
    """
    text = ai_service.ask(safety.SYMPTOM_INSTRUCTIONS, messages)
    return {"reply": text, "urgent": False}
