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

Phase 2 (now): check the conversation and send back a placeholder reply.
Phase 3: replace get_reply() so it asks the AI through ai_service.py.
"""

import time

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


def get_reply(messages):
    """
    Return the assistant's reply to the latest message.

    PLACEHOLDER: the AI is connected in Phase 3. For now this confirms that
    the message travelled from the browser to the server and back.
    """
    # TEMPORARY: pause briefly so we can see the loading indicator while
    # testing. Delete this line in Phase 3, when the AI adds a real wait.
    time.sleep(0.8)

    latest = messages[-1]["content"].strip()
    if len(latest) > 120:
        latest = latest[:120] + "..."

    return (
        "The AI isn't connected yet, so this is a placeholder reply. "
        f'The server received your message: "{latest}" '
        "Once the AI is connected, general information about your symptoms "
        "will appear here."
    )
