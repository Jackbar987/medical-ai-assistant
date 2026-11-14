"""
medication_assistant.py - logic for the Medication Information Assistant.

Phase 2 (now): check the medication name and send back placeholder sections
in the same shape the real answer will have.
Phase 5: look the medication up in trusted sources (MedlinePlus, DailyMed,
FDA labels), then ask the AI to put that source text into plain language.

The answer always has this shape, so the page can show it consistently:

    {
        "name": "ibuprofen",
        "summary": "...",
        "uses": ["...", "..."],
        "side_effects": ["...", "..."],
        "precautions": ["...", "..."],
        "sources": [{"title": "...", "url": "https://..."}],
    }
"""

import re
import time
from urllib.parse import urlencode

MAX_NAME_LENGTH = 100
MAX_QUESTION_LENGTH = 1000

# Medication names use letters, numbers, spaces and a little punctuation,
# for example "amoxicillin-clavulanate" or "vitamin B12". Anything else
# (such as a question mark) usually means someone typed a question instead.
# This pattern is a "regular expression": a compact way to describe text.
#   ^ and $       the whole name must match, start to end
#   [A-Za-z0-9]   the first character is a letter or number
#   [...]*        followed by any number of the allowed characters
ALLOWED_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-'.,/()+&]*$")


def clean_medication_name(name):
    """
    Check a medication name typed by the user.

    Returns (clean_name, None) when it is usable, or (None, error_message).
    """
    if not isinstance(name, str) or name.strip() == "":
        return None, "Type the name of a medication, for example ibuprofen."

    # Collapse runs of spaces into one, and remove spaces at either end.
    name = " ".join(name.split())

    if len(name) > MAX_NAME_LENGTH:
        return None, f"Medication names can be up to {MAX_NAME_LENGTH} characters."

    if not ALLOWED_NAME.match(name):
        return None, (
            "Type just the medication's name, such as ibuprofen. "
            "You can ask questions about it after searching."
        )

    return name, None


def medlineplus_link(name):
    """
    Build a link to MedlinePlus's drug information matches for a name.

    MedlinePlus Connect is a free service from the U.S. National Library of
    Medicine. The long code (2.16.840.1.113883.6.69) tells it we are asking
    about a medication. urlencode() makes the name safe to put in a web
    address, for example turning spaces into "+".
    """
    query = urlencode({
        "mainSearchCriteria.v.cs": "2.16.840.1.113883.6.69",
        "mainSearchCriteria.v.dn": name,
        "informationRecipient.languageCode.c": "en",
    })
    return "https://connect.medlineplus.gov/application?" + query


def look_up(name):
    """
    Return information about a medication.

    PLACEHOLDER: the real lookup is added in Phase 5. Until then every
    section says what it will contain. We deliberately do not make up any
    medical information here, not even as an example.
    """
    # TEMPORARY: pause so the "Looking up" state is visible. Delete in Phase 5.
    time.sleep(0.8)

    return {
        "name": name,
        "summary": (
            "Placeholder: looking up medications isn't connected yet. Once it "
            "is, this page will show information from trusted sources, "
            "explained in plain language."
        ),
        "uses": [
            "What this medication is generally used for will be listed here.",
        ],
        "side_effects": [
            "Common side effects from the official label will be listed here.",
        ],
        "precautions": [
            "Important warnings and precautions will be listed here, including "
            "who should check with a doctor or pharmacist before using it.",
        ],
        "sources": [
            {
                "title": f"MedlinePlus drug information matching \"{name}\"",
                "url": medlineplus_link(name),
            },
        ],
    }


def validate_question(question):
    """Return None if the follow-up question is usable, or an error message."""
    if not isinstance(question, str) or question.strip() == "":
        return "Type a question before pressing Ask."

    if len(question) > MAX_QUESTION_LENGTH:
        return f"Questions can be up to {MAX_QUESTION_LENGTH} characters. Shorten your question and try again."

    return None


def answer_question(name, question):
    """
    Answer a follow-up question about a medication.

    PLACEHOLDER: added in Phase 5, using the same trusted source text.
    The real version must refuse personal dosing and must not advise
    starting, stopping or combining medications.
    """
    time.sleep(0.8)  # TEMPORARY, as in look_up()

    question = question.strip()
    if len(question) > 120:
        question = question[:120] + "..."

    return (
        f'The server received your question about {name}: "{question}" '
        "Answers will appear here once the lookup and AI are connected."
    )
