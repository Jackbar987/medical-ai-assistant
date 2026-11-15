"""
medication_assistant.py - logic for the Medication Information Assistant.

How a search works (Phase 5):
1. clean_medication_name() checks what the person typed.
2. find_label() asks openFDA (the U.S. Food and Drug Administration's free
   public data service) for the official drug label of that medication.
3. label_source_text() collects the label's sections about uses, warnings
   and side effects. Dosing sections are left out on purpose, because this
   app must never tell anyone how much to take.
4. simplify() asks the AI to rewrite those sections in plain language,
   using only what the label says.

The answer always has this shape, so the page can show it consistently:

    {
        "name": "ibuprofen",
        "summary": "...",
        "uses": ["...", "..."],
        "side_effects": ["...", "..."],
        "precautions": ["...", "..."],
        "label": {"title": "...", "manufacturer": "...", "type": "...", "updated": "..."},
        "set_id": "...",
        "sources": [{"title": "...", "url": "https://..."}],
    }
"""

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from backend import ai_service, safety

logger = logging.getLogger(__name__)

MAX_NAME_LENGTH = 100
MAX_QUESTION_LENGTH = 1000
MAX_HISTORY = 10

# Medication names use letters, numbers, spaces and a little punctuation,
# for example "amoxicillin-clavulanate" or "vitamin B12". Anything else
# (such as a question mark) usually means someone typed a question instead.
# This pattern is a "regular expression": a compact way to describe text.
#   ^ and $       the whole name must match, start to end
#   [A-Za-z0-9]   the first character is a letter or number
#   [...]*        followed by any number of the allowed characters
ALLOWED_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-'.,/()+&]*$")

# A label's set ID looks like 955484a6-2a7a-4b15-a9b4-e888ed5de04c.
SET_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

OPENFDA_URL = "https://api.fda.gov/drug/label.json"

# The label sections we use, in the order the AI reads them. Prescription
# labels and over-the-counter labels use different section names, so both
# kinds are listed. Dosing sections are deliberately not included.
LABEL_SECTIONS = [
    ("boxed_warning", "Boxed warning (the FDA's most serious kind of warning)"),
    ("purpose", "Purpose"),
    ("indications_and_usage", "Uses"),
    ("contraindications", "Contraindications (who should not use it)"),
    ("do_not_use", "Do not use"),
    ("ask_doctor", "Ask a doctor before use if"),
    ("ask_doctor_or_pharmacist", "Ask a doctor or pharmacist before use if"),
    ("when_using", "When using this product"),
    ("stop_use", "Stop use and ask a doctor if"),
    ("warnings_and_cautions", "Warnings and precautions"),
    ("warnings", "Warnings"),
    ("adverse_reactions", "Adverse reactions (side effects)"),
    ("drug_interactions", "Drug interactions"),
    ("pregnancy_or_breast_feeding", "Pregnancy or breast-feeding"),
]
MAX_SECTION_LENGTH = 3000   # characters kept from each section
MAX_SOURCE_LENGTH = 20000   # characters of label text sent to the AI


class MedicationError(Exception):
    """A problem finding the medication, explained for the user."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------
# 1. Checking what the person typed
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 2. Finding the FDA label
# ---------------------------------------------------------------------------

def _query_openfda(search, limit):
    """
    Send one search to openFDA and return the list of labels it found.

    openFDA is a public web API: we build a web address containing our
    search, request it, and get JSON back. An optional free API key
    (OPENFDA_API_KEY) raises the daily request limit.
    """
    params = {"search": search, "limit": str(limit)}
    api_key = os.getenv("OPENFDA_API_KEY", "").strip()
    if api_key:
        params["api_key"] = api_key
    url = OPENFDA_URL + "?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return []  # openFDA answers 404 when nothing matches
        if error.code == 429:
            logger.warning("openFDA rate limit reached.")
            raise MedicationError("The FDA label service is busy. Wait a minute and try again.", 503)
        logger.error("openFDA error: status %s", error.code)
        raise MedicationError("The FDA label service had a problem. Try again in a moment.", 503)
    except (urllib.error.URLError, TimeoutError):
        logger.warning("Could not reach openFDA.")
        raise MedicationError("The FDA label service couldn't be reached. Try again in a moment.", 503)
    except ValueError:
        logger.error("openFDA sent something that isn't JSON.")
        raise MedicationError("The FDA label service had a problem. Try again in a moment.", 503)

    return data.get("results", [])


def _names(label, field):
    """Return a label's names from its "openfda" block, such as brand_name."""
    return [n for n in label.get("openfda", {}).get(field, []) if isinstance(n, str)]


def _score(label, name):
    """
    Give a label points for how well it fits, so we can pick the best one.
    Many companies make the same medicine, so a search often finds dozens.
    """
    wanted = name.lower()
    generic = [n.lower() for n in _names(label, "generic_name")]
    brand = [n.lower() for n in _names(label, "brand_name")]
    score = 0
    if wanted in generic or wanted in brand:
        score += 10  # an exact name match is best
    if label.get("indications_and_usage") or label.get("purpose"):
        score += 5   # it says what the medicine is for
    if label.get("adverse_reactions") or label.get("warnings") or label.get("warnings_and_cautions"):
        score += 3   # it has safety information
    return score


def find_label(name):
    """
    Find the best FDA label for a medication name.

    Raises MedicationError if no label is found or openFDA can't be reached.
    """
    # Look for the name as either the generic name or the brand name.
    # A space between the two parts means "either one" in openFDA searches.
    search = f'openfda.generic_name:"{name}" openfda.brand_name:"{name}"'
    labels = _query_openfda(search, limit=10)

    if not labels:
        raise MedicationError(
            f'No FDA label was found for "{name}". Check the spelling, or try the generic name '
            "(for example, ibuprofen instead of a brand name).",
            404,
        )

    # Highest score first; among equal scores, the most recently updated.
    labels.sort(key=lambda label: (_score(label, name), label.get("effective_time", "")), reverse=True)
    return labels[0]


def find_label_by_set_id(set_id):
    """Fetch one specific label again, for follow-up questions."""
    labels = _query_openfda(f'set_id:"{set_id}"', limit=1)
    if not labels:
        raise MedicationError("That label couldn't be found anymore. Search for the medication again.", 404)
    return labels[0]


def label_source_text(label):
    """
    Collect the label sections we use into one block of text for the AI.
    Each section starts with a heading, so the AI knows where text came from.
    """
    parts = []
    for field, heading in LABEL_SECTIONS:
        values = label.get(field)
        if not values:
            continue
        text = " ".join(v for v in values if isinstance(v, str)).strip()
        if len(text) > MAX_SECTION_LENGTH:
            text = text[:MAX_SECTION_LENGTH] + " [section shortened]"
        parts.append(f"## {heading}\n{text}")

    source = "\n\n".join(parts)
    if len(source) > MAX_SOURCE_LENGTH:
        source = source[:MAX_SOURCE_LENGTH] + "\n[label text shortened]"
    return source


def _format_date(effective_time):
    """Turn openFDA's "20260315" into "March 15, 2026"."""
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    if isinstance(effective_time, str) and len(effective_time) >= 8 and effective_time[:8].isdigit():
        year, month, day = effective_time[:4], int(effective_time[4:6]), int(effective_time[6:8])
        if 1 <= month <= 12:
            return f"{months[month - 1]} {day}, {year}"
    return "Unknown"


def label_info(label):
    """Short facts about the label, shown above the explanation."""
    brand = _names(label, "brand_name")
    generic = _names(label, "generic_name")
    manufacturer = _names(label, "manufacturer_name")
    product_type = _names(label, "product_type")

    title = brand[0] if brand else (generic[0] if generic else "FDA drug label")
    if brand and generic and brand[0].lower() != generic[0].lower():
        title = f"{brand[0]} ({generic[0].lower()})"

    kind = ""  # empty when the label doesn't say
    if product_type:
        if "OTC" in product_type[0].upper():
            kind = "over-the-counter"
        elif "PRESCRIPTION" in product_type[0].upper():
            kind = "prescription"

    return {
        "title": title,
        "manufacturer": manufacturer[0] if manufacturer else "Unknown manufacturer",
        "type": kind,
        "updated": _format_date(label.get("effective_time")),
    }


def medlineplus_link(name):
    """
    Build a link to MedlinePlus's drug information matches for a name.

    MedlinePlus Connect is a free service from the U.S. National Library of
    Medicine. The long code (2.16.840.1.113883.6.69) tells it we are asking
    about a medication. urlencode() makes the name safe to put in a web
    address, for example turning spaces into "+".
    """
    query = urllib.parse.urlencode({
        "mainSearchCriteria.v.cs": "2.16.840.1.113883.6.69",
        "mainSearchCriteria.v.dn": name,
        "informationRecipient.languageCode.c": "en",
    })
    return "https://connect.medlineplus.gov/application?" + query


def dailymed_link(set_id):
    """The label's page on DailyMed, the National Library of Medicine's label site."""
    return "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=" + urllib.parse.quote(set_id)


# ---------------------------------------------------------------------------
# 3. Simplifying the label with the AI
# ---------------------------------------------------------------------------

def _wrap_label(source_text):
    """Mark where the label text starts and ends (see safety.py)."""
    return f"<label>\n{source_text}\n</label>"


def _parse_sections(text):
    """
    Read the AI's JSON answer and check it has the expected shape.

    We ask the AI for JSON so the page can show each part in its own
    section. AI output isn't guaranteed to be valid, so we check carefully.
    """
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    data = json.loads(text[start:end + 1])

    def clean_list(key):
        items = data.get(key, [])
        if not isinstance(items, list):
            raise ValueError(f"{key} is not a list")
        return [str(item).strip() for item in items if str(item).strip()][:8]

    summary = data.get("summary", "")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("summary missing")

    return {
        "summary": summary.strip(),
        "uses": clean_list("uses"),
        "side_effects": clean_list("side_effects"),
        "precautions": clean_list("precautions"),
    }


def look_up(name):
    """
    Find a medication's FDA label and simplify it.

    Raises MedicationError (no label, FDA service problem) or
    ai_service.AIServiceError (AI problem).
    """
    label = find_label(name)
    source = label_source_text(label)
    if not source:
        raise MedicationError(
            f'An FDA label was found for "{name}", but it has no sections about uses or safety. '
            "Try the generic name instead.",
            404,
        )

    message = _wrap_label(source) + f'\n\nThe person searched for "{name}". Simplify this label as instructed.'
    reply = ai_service.ask(safety.MEDICATION_INSTRUCTIONS, [{"role": "user", "content": message}])

    try:
        sections = _parse_sections(reply)
    except (ValueError, json.JSONDecodeError):
        logger.warning("The AI's medication answer wasn't valid JSON.")
        raise ai_service.AIServiceError("The answer couldn't be put together. Try searching again.")

    set_id = label.get("set_id", "")
    sources = []
    if isinstance(set_id, str) and SET_ID_PATTERN.match(set_id):
        sources.append({"title": "The FDA label this summary is based on (DailyMed)", "url": dailymed_link(set_id)})
    sources.append({"title": f'MedlinePlus drug information matching "{name}"', "url": medlineplus_link(name)})

    return {
        "name": name,
        **sections,
        "label": label_info(label),
        "set_id": set_id if SET_ID_PATTERN.match(str(set_id)) else "",
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# 4. Follow-up questions
# ---------------------------------------------------------------------------

def validate_question(data):
    """
    Check a follow-up question sent by the browser.

    Returns (set_id, name, question, history, None) when usable, or
    (None, None, None, None, error_message).
    """
    set_id = data.get("set_id")
    question = data.get("question")
    history = data.get("history", [])
    name, name_error = clean_medication_name(data.get("medication"))

    if not isinstance(set_id, str) or not SET_ID_PATTERN.match(set_id) or name_error:
        return None, None, None, None, "Search for a medication before asking a question."

    if not isinstance(question, str) or question.strip() == "":
        return None, None, None, None, "Type a question before pressing Ask."

    if len(question) > MAX_QUESTION_LENGTH:
        return None, None, None, None, f"Questions can be up to {MAX_QUESTION_LENGTH} characters. Shorten your question and try again."

    if not isinstance(history, list):
        history = []
    clean_history = [
        {"question": item["question"][:MAX_QUESTION_LENGTH], "answer": item["answer"][:5000]}
        for item in history[-MAX_HISTORY:]
        if isinstance(item, dict) and isinstance(item.get("question"), str) and isinstance(item.get("answer"), str)
    ]

    return set_id, name, question.strip(), clean_history, None


def answer_question(set_id, name, question, history):
    """
    Answer a follow-up question using the same FDA label. The server keeps
    nothing between requests, so the label is fetched again by its set ID.
    """
    label = find_label_by_set_id(set_id)
    source = label_source_text(label)

    messages = [
        {"role": "user", "content": _wrap_label(source) + f"\n\nI have questions about {name}, based on this label."},
        {"role": "assistant", "content": "Of course. What would you like to know?"},
    ]
    for item in history:
        messages.append({"role": "user", "content": item["question"]})
        messages.append({"role": "assistant", "content": item["answer"]})
    messages.append({"role": "user", "content": question})

    return ai_service.ask(safety.MEDICATION_QUESTION_INSTRUCTIONS, messages)
