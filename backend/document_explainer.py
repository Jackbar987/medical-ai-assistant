"""
document_explainer.py - logic for the Medical Document Explainer.

How a document is explained:
1. read_uploaded_pdf() checks the upload (type, size, real PDF).
2. extract_text() pulls the text out of the PDF with PyMuPDF, keeping
   each line of a table together (see _page_lines below).
   Or, if the person pasted text instead, clean_pasted_text() checks it.
3. explain() sends that text to the AI with the document instructions
   from safety.py.
4. Follow-up questions: the browser sends the extracted text back with
   each question, because the server keeps nothing between requests.

Privacy: the uploaded file is only read into memory for the length of one
request. It is never saved to disk, so nothing is left behind afterwards.
(This also suits Vercel, which has no permanent disk.)
"""

import pymupdf

from backend import ai_service, safety

# Vercel rejects requests larger than about 4.5 MB, so we stay below that.
MAX_FILE_SIZE = 4 * 1024 * 1024   # 4 MB, in bytes
MAX_PAGES = 10                    # longer documents are refused
MAX_TEXT_LENGTH = 30000           # characters of text sent to the AI
MIN_TEXT_LENGTH = 20              # less than this means "no readable text"
MAX_QUESTION_LENGTH = 1000        # characters in one follow-up question
MAX_HISTORY = 10                  # earlier questions and answers sent along

# Two words further apart than this (in points; 72 points = 1 inch) are
# treated as being in different table columns, and get " | " between them.
COLUMN_GAP = 10
# Words whose vertical centres are this close are on the same line.
SAME_LINE = 3


class DocumentError(Exception):
    """A problem with the document itself, explained for the user."""


# ---------------------------------------------------------------------------
# 1. Checking the upload
# ---------------------------------------------------------------------------

def read_uploaded_pdf(uploaded_file):
    """
    Check an uploaded file and read it into memory.

    Returns a pair: (pdf_bytes, None) when the file is fine, or
    (None, error_message) when it isn't. Every check here is repeated from
    the browser on purpose: the browser's checks are a convenience for the
    user, but anyone can send files to our server without using our page.
    """
    if uploaded_file is None or uploaded_file.filename == "":
        return None, "Choose a PDF file before pressing Explain document."

    if not uploaded_file.filename.lower().endswith(".pdf"):
        return None, "Only PDF files can be explained. Choose a file whose name ends in .pdf."

    # Read at most one byte more than the limit. If we get that extra byte,
    # the file is too big, and we never load a huge file into memory.
    data = uploaded_file.read(MAX_FILE_SIZE + 1)

    if len(data) == 0:
        return None, "This file is empty. Choose another PDF."

    if len(data) > MAX_FILE_SIZE:
        return None, "This file is larger than 4 MB. Choose a smaller PDF."

    # Every real PDF starts with the characters "%PDF-". Checking this stops
    # someone from renaming another kind of file to ".pdf".
    if not data.startswith(b"%PDF-"):
        return None, "This file isn't a real PDF, even though its name ends in .pdf. Choose another file."

    return data, None


# ---------------------------------------------------------------------------
# 2. Extracting the text
# ---------------------------------------------------------------------------

def _page_lines(page):
    """
    Rebuild a page's text line by line from the position of each word.

    PyMuPDF's simplest text extraction puts each table cell on its own line,
    which separates a test's name from its value, units and range. Instead,
    we ask for every word with its position on the page, group words that
    sit at the same height into one line, and put " | " where there is a
    wide gap (a new column). A table row then comes out as, for example:
        Glucose, fasting | 104 | H | mg/dL | 70 - 99
    """
    # Each word is (x0, y0, x1, y1, text, ...): its box on the page and text.
    words = page.get_text("words")

    # Sort from top to bottom, then left to right, using each word's middle.
    words.sort(key=lambda w: ((w[1] + w[3]) / 2, w[0]))

    rows = []
    for word in words:
        middle = (word[1] + word[3]) / 2
        if rows and abs(rows[-1]["middle"] - middle) <= SAME_LINE:
            rows[-1]["words"].append(word)
        else:
            rows.append({"middle": middle, "words": [word]})

    lines = []
    for row in rows:
        row_words = sorted(row["words"], key=lambda w: w[0])
        line = row_words[0][4]
        for previous, current in zip(row_words, row_words[1:]):
            gap = current[0] - previous[2]
            line += (" | " if gap > COLUMN_GAP else " ") + current[4]
        lines.append(line)
    return lines


def extract_text(pdf_bytes):
    """
    Return the document's text, ready to send to the AI.

    Raises DocumentError if the PDF can't be read, is locked, is too long,
    or has no text (for example, a scanned image).
    """
    try:
        document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        raise DocumentError("This PDF couldn't be opened. It may be damaged. Try another file.")

    with document:
        if document.needs_pass:
            raise DocumentError("This PDF is password-protected. Remove the password and upload it again.")

        if document.page_count > MAX_PAGES:
            raise DocumentError(
                f"This PDF has {document.page_count} pages. Upload a document of {MAX_PAGES} pages or fewer."
            )

        parts = []
        for number, page in enumerate(document, start=1):
            lines = _page_lines(page)
            if lines:
                parts.append(f"--- Page {number} ---\n" + "\n".join(lines))

    text = "\n\n".join(parts).strip()

    if len(text) < MIN_TEXT_LENGTH:
        raise DocumentError(
            "No readable text was found in this PDF. It may be a scanned image or a photo, "
            "which can't be read yet. Try a PDF you can select text in."
        )

    if len(text) > MAX_TEXT_LENGTH:
        raise DocumentError("This document has too much text to explain at once. Try a shorter document.")

    return text


def clean_pasted_text(text):
    """
    Check text that the person pasted instead of uploading a PDF.

    Returns (clean_text, None) when it is usable, or (None, error_message).
    """
    if not isinstance(text, str):
        return None, "Paste the text of your document before pressing Explain document."

    # Windows uses "\r\n" for new lines; turn every kind into a plain "\n".
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    if len(text) < MIN_TEXT_LENGTH:
        return None, "Paste a bit more of your document. There isn't enough text to explain."

    if len(text) > MAX_TEXT_LENGTH:
        return None, f"That's more than {MAX_TEXT_LENGTH:,} characters. Paste a shorter part of the document."

    return text, None


# ---------------------------------------------------------------------------
# 3. Explaining and answering questions
# ---------------------------------------------------------------------------

def _wrap_document(text):
    """
    Put the document between clear markers. The AI's instructions tell it
    that everything between these markers is content to explain, never
    instructions to follow, even if the document contains commands.
    """
    return f"<document>\n{text}\n</document>"


def explain(document_text):
    """
    Ask the AI to explain the document. Raises ai_service.AIServiceError if
    the AI can't answer.
    """
    message = (
        _wrap_document(document_text)
        + "\n\nPlease explain this document in plain language, following your instructions."
    )
    return ai_service.ask(safety.DOCUMENT_INSTRUCTIONS, [{"role": "user", "content": message}])


def validate_question(data):
    """
    Check a follow-up question sent by the browser.

    Returns (question, document_text, history, None) when usable, or
    (None, None, None, error_message).
    """
    question = data.get("question")
    document_text = data.get("document_text")
    history = data.get("history", [])

    if not isinstance(question, str) or question.strip() == "":
        return None, None, None, "Type a question before pressing Ask."

    if len(question) > MAX_QUESTION_LENGTH:
        return None, None, None, f"Questions can be up to {MAX_QUESTION_LENGTH} characters. Shorten your question and try again."

    if not isinstance(document_text, str) or len(document_text.strip()) < MIN_TEXT_LENGTH:
        return None, None, None, "Explain a document first, then ask questions about it."

    if len(document_text) > MAX_TEXT_LENGTH:
        return None, None, None, "The document text was too long. Clear the document and upload it again."

    if not isinstance(history, list):
        return None, None, None, "The questions could not be read. Clear the document and try again."

    clean_history = []
    for item in history[-MAX_HISTORY:]:
        if (
            isinstance(item, dict)
            and isinstance(item.get("question"), str)
            and isinstance(item.get("answer"), str)
        ):
            clean_history.append({
                "question": item["question"][:MAX_QUESTION_LENGTH],
                "answer": item["answer"][:5000],
            })

    return question.strip(), document_text, clean_history, None


def answer_question(question, document_text, history):
    """
    Answer a follow-up question about the document, using the document and
    the earlier questions and answers as context.
    """
    # Rebuild the conversation: the document first, then each earlier
    # question with its answer, then the new question.
    messages = [
        {"role": "user", "content": _wrap_document(document_text) + "\n\nI have questions about this document."},
        {"role": "assistant", "content": "Of course. What would you like to know about it?"},
    ]
    for item in history:
        messages.append({"role": "user", "content": item["question"]})
        messages.append({"role": "assistant", "content": item["answer"]})
    messages.append({"role": "user", "content": question})

    return ai_service.ask(safety.DOCUMENT_QUESTION_INSTRUCTIONS, messages)
