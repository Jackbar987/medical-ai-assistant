/*
  documents.js - makes the Document Explainer page work.

  The steps, in order:

    1. The user chooses a PDF (button or drag and drop), or switches to
       "Paste text" and pastes the document's text. We check the PDF's type
       and size right away, but we do NOT upload it yet.
    2. They press "Explain document". We send the file (with a progress
       bar) or the pasted text to the server.
    3. The server checks the file and sends back an explanation as JSON.
    4. They can ask follow-up questions about the document.
    5. "Clear document" forgets everything and starts over.

  Nothing is saved: the server reads the file once and throws it away, and
  this page forgets everything when it is cleared or reloaded.
*/

// Must match MAX_FILE_SIZE and MIN_TEXT_LENGTH in backend/document_explainer.py.
const MAX_FILE_SIZE = 4 * 1024 * 1024; // 4 MB in bytes
const MIN_PASTE_LENGTH = 20;

// "pdf" or "paste": which way of adding a document is selected.
let mode = "pdf";

let selectedFile = null; // the File object the user chose
let isBusy = false;      // true while uploading or waiting for an answer

// The text the server read from the PDF. The server remembers nothing
// between requests, so we send this back with every follow-up question.
let documentText = "";

// Earlier questions and answers, sent along so the AI knows the context.
let qaHistory = [];

// Parts of the page.
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const fileCard = document.getElementById("file-card");
const fileName = document.getElementById("file-name");
const fileSize = document.getElementById("file-size");
const removeButton = document.getElementById("remove-file");
const explainButton = document.getElementById("explain-button");
const modeSwitch = document.getElementById("mode-switch");
const modePdfButton = document.getElementById("mode-pdf");
const modePasteButton = document.getElementById("mode-paste");
const pdfMode = document.getElementById("pdf-mode");
const pasteMode = document.getElementById("paste-mode");
const pasteInput = document.getElementById("paste-input");
const pasteCount = document.getElementById("paste-count");
const progress = document.getElementById("progress");
const progressText = document.getElementById("progress-text");
const progressPercent = document.getElementById("progress-percent");
const progressTrack = document.getElementById("progress-track");
const progressBar = document.getElementById("progress-bar");
const uploadError = document.getElementById("upload-error");

const resultPanel = document.getElementById("result-panel");
const explanationTitle = document.getElementById("explanation-title");
const explanation = document.getElementById("explanation");
const extractedText = document.getElementById("extracted-text");
const extractedBox = document.getElementById("extracted");
const clearButton = document.getElementById("clear-document");
const qaList = document.getElementById("qa-list");
const questionForm = document.getElementById("question-form");
const questionInput = document.getElementById("question-input");
const askButton = document.getElementById("ask-button");
const questionError = document.getElementById("question-error");


/* ---------- Small helpers ---------- */

// Turn a number of bytes into "820 KB" or "1.4 MB".
function formatSize(bytes) {
  if (bytes < 1024 * 1024) {
    return Math.max(1, Math.round(bytes / 1024)) + " KB";
  }
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function showMessage(element, message) {
  element.textContent = message;
  element.hidden = false;
}

function hideMessage(element) {
  element.textContent = "";
  element.hidden = true;
}

// Turn the Explain button on only when there is something to explain.
function updateExplainButton() {
  if (mode === "pdf") {
    explainButton.disabled = isBusy || selectedFile === null;
  } else {
    explainButton.disabled = isBusy || pasteInput.value.trim().length < MIN_PASTE_LENGTH;
  }
}

// Check a file before uploading. Returns an error message, or null if fine.
function checkFile(file) {
  const looksLikePdf =
    file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf";

  if (!looksLikePdf) {
    return "This file isn't a PDF. Choose a file whose name ends in .pdf.";
  }
  if (file.size === 0) {
    return "This file is empty. Choose another PDF.";
  }
  if (file.size > MAX_FILE_SIZE) {
    return "This file is larger than 4 MB. Choose a smaller PDF.";
  }
  return null;
}


/* ---------- Choosing a file ---------- */

function selectFile(file) {
  hideMessage(uploadError);

  const problem = checkFile(file);
  if (problem) {
    showMessage(uploadError, problem);
    return;
  }

  selectedFile = file;
  fileName.textContent = file.name; // textContent: file names can contain anything
  fileSize.textContent = formatSize(file.size);
  dropzone.hidden = true;
  fileCard.hidden = false;
  updateExplainButton();
}

function removeFile() {
  selectedFile = null;
  fileInput.value = ""; // lets the same file be chosen again later
  fileCard.hidden = true;
  dropzone.hidden = false;
  updateExplainButton();
  hideMessage(uploadError);
}

// The "Choose a PDF" button opens the file picker; this runs after a choice.
fileInput.addEventListener("change", function () {
  if (fileInput.files.length > 0) {
    selectFile(fileInput.files[0]);
  }
});

removeButton.addEventListener("click", removeFile);

// Drag and drop. By default, a browser opens a dropped file in the tab, so we
// call preventDefault() to handle the file ourselves instead.
["dragenter", "dragover"].forEach(function (eventName) {
  dropzone.addEventListener(eventName, function (event) {
    event.preventDefault();
    dropzone.classList.add("is-dragging");
  });
});

["dragleave", "drop"].forEach(function (eventName) {
  dropzone.addEventListener(eventName, function (event) {
    event.preventDefault();
    dropzone.classList.remove("is-dragging");
  });
});

dropzone.addEventListener("drop", function (event) {
  const files = event.dataTransfer.files;
  if (files.length > 1) {
    showMessage(uploadError, "Drop one PDF at a time.");
  } else if (files.length === 1) {
    selectFile(files[0]);
  }
});

// Stop a file dropped just outside the drop area from replacing the page.
window.addEventListener("dragover", function (event) { event.preventDefault(); });
window.addEventListener("drop", function (event) { event.preventDefault(); });


/* ---------- Uploading and explaining ---------- */

function setProgress(fraction) {
  const percent = Math.round(fraction * 100);
  progressBar.style.width = percent + "%";
  progressPercent.textContent = percent + "%";
  progressTrack.setAttribute("aria-valuenow", String(percent));
}

function uploadAndExplain() {
  if (!selectedFile || isBusy) {
    return;
  }

  isBusy = true;
  explainButton.disabled = true;
  removeButton.disabled = true;
  hideMessage(uploadError);
  progress.hidden = false;
  progress.classList.remove("is-processing");
  progressText.textContent = "Uploading";
  setProgress(0);

  // FormData packages a file the same way an HTML form upload would.
  // "document" is the name the server looks for in request.files.
  const formData = new FormData();
  formData.append("document", selectedFile);

  // We use XMLHttpRequest instead of fetch() here because it can report
  // upload progress, which fetch() cannot do yet.
  const request = new XMLHttpRequest();
  request.open("POST", "/api/documents/explain");
  request.responseType = "json"; // read the reply as JSON automatically

  // Runs repeatedly while the file is being sent.
  request.upload.addEventListener("progress", function (event) {
    if (event.lengthComputable) {
      setProgress(event.loaded / event.total);
    }
  });

  // Runs once the whole file has reached the server.
  request.upload.addEventListener("load", function () {
    setProgress(1);
    progressText.textContent = "Reading and explaining your document. This can take up to 30 seconds";
    progressPercent.textContent = "";
    progress.classList.add("is-processing");
  });

  // Runs when the server's answer arrives (successful or not).
  request.addEventListener("load", function () {
    // request.response is null if the server didn't send valid JSON.
    const data = request.response;

    if (request.status === 200 && data && typeof data.explanation === "string") {
      showResult(data.explanation, data.document_text || "");
    } else if (data && data.error) {
      finishUpload();
      showMessage(uploadError, data.error);
    } else if (request.status === 413) {
      // 413 means "too large". Our hosting service can send this before the
      // request even reaches Flask, in which case there is no JSON message.
      finishUpload();
      showMessage(uploadError, "This file is larger than 4 MB. Choose a smaller PDF.");
    } else {
      finishUpload();
      showMessage(uploadError, "Something went wrong on the server. Wait a moment and try again.");
    }
  });

  // Runs if the request never reached the server (for example, no internet).
  request.addEventListener("error", function () {
    finishUpload();
    showMessage(uploadError, "Couldn't reach the server. Check your internet connection and try again.");
  });

  request.send(formData);
}

// Put the upload controls back to normal after an upload ends.
function finishUpload() {
  isBusy = false;
  progress.hidden = true;
  updateExplainButton();
  removeButton.disabled = false;
}

function showResult(text, readText) {
  finishUpload();
  explanation.textContent = text; // textContent, never innerHTML
  documentText = readText;
  extractedText.textContent = readText;
  // Pasted text is already visible in the paste box, so only show the
  // "text read from your document" box for PDFs.
  extractedBox.hidden = mode === "paste";
  qaHistory = [];
  explainButton.hidden = true;
  removeButton.hidden = true;
  modeSwitch.hidden = true;
  pasteInput.readOnly = true; // the pasted text can't change after explaining
  resultPanel.hidden = false;
  updateAskButton();

  // Move keyboard and screen reader focus to the new content.
  explanationTitle.focus();
}

// Send pasted text to the server. Text is small, so fetch() is enough here;
// no progress bar is needed, only the "explaining" state.
async function explainPasted() {
  const text = pasteInput.value.trim();
  if (text.length < MIN_PASTE_LENGTH || isBusy) {
    return;
  }

  isBusy = true;
  updateExplainButton();
  hideMessage(uploadError);
  progress.hidden = false;
  progress.classList.add("is-processing");
  progressText.textContent = "Explaining your text. This can take up to 30 seconds";
  setProgress(1);
  progressPercent.textContent = "";

  try {
    const response = await fetch("/api/documents/explain-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text }),
    });

    let data = null;
    try {
      data = await response.json();
    } catch (readError) {
      data = null;
    }

    if (!response.ok || !data || typeof data.explanation !== "string") {
      throw new Error(
        (data && data.error) || "Something went wrong on the server. Wait a moment and try again."
      );
    }

    showResult(data.explanation, data.document_text || text);
  } catch (error) {
    finishUpload();
    if (error instanceof TypeError) {
      showMessage(uploadError, "Couldn't reach the server. Check your internet connection and try again.");
    } else {
      showMessage(uploadError, error.message);
    }
  }
}

// One button explains whichever kind of document is selected.
explainButton.addEventListener("click", function () {
  if (mode === "pdf") {
    uploadAndExplain();
  } else {
    explainPasted();
  }
});


/* ---------- Switching between "Upload a PDF" and "Paste text" ---------- */

function setMode(newMode) {
  if (isBusy) {
    return;
  }
  mode = newMode;
  modePdfButton.setAttribute("aria-pressed", String(mode === "pdf"));
  modePasteButton.setAttribute("aria-pressed", String(mode === "paste"));
  pdfMode.hidden = mode !== "pdf";
  pasteMode.hidden = mode !== "paste";
  hideMessage(uploadError);
  updateExplainButton();
}

modePdfButton.addEventListener("click", function () { setMode("pdf"); });
modePasteButton.addEventListener("click", function () {
  setMode("paste");
  pasteInput.focus();
});

// Keep the character count and the Explain button up to date while typing.
pasteInput.addEventListener("input", function () {
  pasteCount.textContent = pasteInput.value.length.toLocaleString() + " / 30,000";
  updateExplainButton();
});


/* ---------- Follow-up questions ---------- */

function addQuestionAndAnswer(question) {
  const item = document.createElement("div");
  item.className = "qa-item";

  const questionText = document.createElement("p");
  questionText.className = "qa-question";
  questionText.textContent = question;

  const answerText = document.createElement("p");
  answerText.className = "qa-answer is-loading";
  answerText.textContent = "Finding an answer...";

  item.append(questionText, answerText);
  qaList.appendChild(item);
  return { item: item, answer: answerText };
}

function updateAskButton() {
  askButton.disabled = isBusy || questionInput.value.trim() === "";
}

async function askQuestion(question) {
  isBusy = true;
  questionInput.value = "";
  updateAskButton();
  hideMessage(questionError);

  const entry = addQuestionAndAnswer(question);

  try {
    const response = await fetch("/api/documents/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: question,
        document_text: documentText,
        history: qaHistory,
      }),
    });

    let data = null;
    try {
      data = await response.json();
    } catch (readError) {
      data = null;
    }

    if (!response.ok || !data || typeof data.answer !== "string") {
      throw new Error(
        (data && data.error) || "Something went wrong on the server. Wait a moment and ask again."
      );
    }

    entry.answer.textContent = data.answer;
    entry.answer.classList.remove("is-loading");
    // urgent is true when the question mentioned possible emergency signs.
    if (data.urgent === true) {
      entry.answer.classList.add("is-urgent");
    }
    qaHistory.push({ question: question, answer: data.answer });
  } catch (error) {
    // Remove the unanswered question and put it back in the box.
    entry.item.remove();
    questionInput.value = question;
    if (error instanceof TypeError) {
      showMessage(questionError, "Couldn't reach the server. Check your internet connection and ask again.");
    } else {
      showMessage(questionError, error.message);
    }
  } finally {
    isBusy = false;
    updateAskButton();
    questionInput.focus();
  }
}

questionForm.addEventListener("submit", function (event) {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (question !== "" && !isBusy) {
    askQuestion(question);
  }
});

questionInput.addEventListener("input", updateAskButton);


/* ---------- Starting over ---------- */

clearButton.addEventListener("click", function () {
  explanation.textContent = "";
  extractedText.textContent = "";
  documentText = "";
  qaHistory = [];
  qaList.textContent = "";
  questionInput.value = "";
  hideMessage(questionError);
  resultPanel.hidden = true;

  explainButton.hidden = false;
  removeButton.hidden = false;
  modeSwitch.hidden = false;
  pasteInput.readOnly = false;
  pasteInput.value = "";
  pasteCount.textContent = "0 / 30,000";
  removeFile();
  if (mode === "pdf") {
    fileInput.focus();
  } else {
    pasteInput.focus();
  }
});
