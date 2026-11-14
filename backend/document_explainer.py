"""
document_explainer.py - logic for the Medical Document Explainer.

Phase 2 (now): check the uploaded file and send back placeholder text.
Phase 4: extract the PDF's text and ask the AI to explain it.

Privacy: the uploaded file is only read into memory for the length of one
request. It is never saved to disk, so nothing is left behind afterwards.
(This also suits Vercel, which has no permanent disk.)
"""

import time

# Vercel rejects requests larger than about 4.5 MB, so we stay below that.
MAX_FILE_SIZE = 4 * 1024 * 1024  # 4 MB, in bytes
MAX_QUESTION_LENGTH = 1000       # characters in one follow-up question


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


def get_explanation(pdf_bytes):
    """
    Return a plain-language explanation of the document.

    PLACEHOLDER: text extraction and the AI are added in Phase 4.
    """
    # TEMPORARY: pause briefly so we can see the "Reading your document"
    # step while testing. Delete this line in Phase 4.
    time.sleep(1)

    size_kb = max(1, round(len(pdf_bytes) / 1024))
    return (
        f"The server received your PDF ({size_kb} KB) and checked that it is "
        "a real PDF under the size limit.\n\n"
        "Reading the document's text and explaining it are not connected yet. "
        "Once they are, this area will list the tests in your report, explain "
        "each term and abbreviation in everyday words, and show the values, "
        "units and reference ranges exactly as they appear in the document."
    )


def validate_question(question):
    """Return None if the question is usable, or an error message."""
    if not isinstance(question, str) or question.strip() == "":
        return "Type a question before pressing Ask."

    if len(question) > MAX_QUESTION_LENGTH:
        return f"Questions can be up to {MAX_QUESTION_LENGTH} characters. Shorten your question and try again."

    return None


def answer_question(question):
    """
    Answer a follow-up question about the document.

    PLACEHOLDER: added in Phase 4. Because the server remembers nothing
    between requests, the browser will then send the document's extracted
    text along with each question.
    """
    time.sleep(0.8)  # TEMPORARY, as in get_explanation()

    question = question.strip()
    if len(question) > 120:
        question = question[:120] + "..."

    return (
        f'The server received your question: "{question}" '
        "Answers about your document will appear here once the AI is connected."
    )
