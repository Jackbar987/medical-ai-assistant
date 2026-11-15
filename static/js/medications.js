/*
  medications.js - makes the Medication Assistant page work.

    1. The user types a medication name (or clicks an example) and searches.
    2. We send the name to /api/medications/search.
    3. The server answers with JSON in a fixed shape: a summary, lists of
       uses, side effects and precautions, and a list of sources.
    4. We fill in each section of the page from that JSON.
    5. Follow-up questions go to /api/medications/ask with the medication's name.
*/

let currentMedication = null; // the name shown in the results
let isBusy = false;           // true while waiting for the server

// Parts of the page.
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const searchButton = document.getElementById("search-button");
const searchStatus = document.getElementById("search-status");
const searchError = document.getElementById("search-error");
const exampleButtons = document.querySelectorAll(".example");

const resultPanel = document.getElementById("result-panel");
const resultTitle = document.getElementById("result-title");
const resultSummary = document.getElementById("result-summary");
const usesList = document.getElementById("uses-list");
const sideEffectsList = document.getElementById("side-effects-list");
const precautionsList = document.getElementById("precautions-list");
const sourcesList = document.getElementById("sources-list");

const qaList = document.getElementById("qa-list");
const questionForm = document.getElementById("question-form");
const questionInput = document.getElementById("question-input");
const askButton = document.getElementById("ask-button");
const questionError = document.getElementById("question-error");


/* ---------- Small helpers ---------- */

function showMessage(element, message) {
  element.textContent = message;
  element.hidden = false;
}

function hideMessage(element) {
  element.textContent = "";
  element.hidden = true;
}

function updateButtons() {
  searchButton.disabled = isBusy || searchInput.value.trim() === "";
  askButton.disabled = isBusy || questionInput.value.trim() === "";
  exampleButtons.forEach(function (button) {
    button.disabled = isBusy;
  });
}

// Send JSON to our server and return the JSON reply.
// Throws an Error with a readable message if anything goes wrong.
async function postJson(url, body) {
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (networkError) {
    throw new Error("Couldn't reach the server. Check your internet connection and try again.");
  }

  let data = null;
  try {
    data = await response.json();
  } catch (readError) {
    data = null;
  }

  if (!response.ok || !data) {
    throw new Error(
      (data && data.error) || "Something went wrong on the server. Wait a moment and try again."
    );
  }
  return data;
}

// Replace a list's contents with one <li> per item.
function fillList(listElement, items) {
  listElement.textContent = ""; // remove old items
  (items || []).forEach(function (item) {
    const li = document.createElement("li");
    li.textContent = item; // textContent, never innerHTML
    listElement.appendChild(li);
  });
}

// Source links need extra care, because a link can run code if its address
// starts with "javascript:". We only show links that start with "https://".
function fillSources(sources) {
  sourcesList.textContent = "";
  (sources || []).forEach(function (source) {
    if (typeof source.url !== "string" || !source.url.startsWith("https://")) {
      return; // skip anything that isn't a normal secure web address
    }

    const li = document.createElement("li");
    const link = document.createElement("a");
    link.href = source.url;
    link.textContent = source.title || source.url;
    // Open in a new tab. "noopener" stops the new page from controlling ours.
    link.target = "_blank";
    link.rel = "noopener noreferrer";

    const note = document.createElement("span");
    note.className = "visually-hidden";
    note.textContent = " (opens in a new tab)";
    link.appendChild(note);

    li.appendChild(link);
    sourcesList.appendChild(li);
  });
}


/* ---------- Searching ---------- */

async function search(name) {
  isBusy = true;
  updateButtons();
  hideMessage(searchError);
  showMessage(searchStatus, "Looking up " + name + "...");

  try {
    const data = await postJson("/api/medications/search", { name: name });

    currentMedication = data.name;
    resultTitle.textContent = data.name;
    resultSummary.textContent = data.summary || "";
    fillList(usesList, data.uses);
    fillList(sideEffectsList, data.side_effects);
    fillList(precautionsList, data.precautions);
    fillSources(data.sources);

    // A new medication starts with no questions.
    qaList.textContent = "";
    questionInput.value = "";
    hideMessage(questionError);

    hideMessage(searchStatus);
    resultPanel.hidden = false;
    resultTitle.focus(); // move keyboard and screen reader focus to the results
  } catch (error) {
    hideMessage(searchStatus);
    showMessage(searchError, error.message);
    searchInput.focus();
  } finally {
    isBusy = false;
    updateButtons();
  }
}

searchForm.addEventListener("submit", function (event) {
  event.preventDefault();
  const name = searchInput.value.trim();
  if (name !== "" && !isBusy) {
    search(name);
  }
});

// Clicking an example fills in the box and searches straight away.
exampleButtons.forEach(function (button) {
  button.addEventListener("click", function () {
    searchInput.value = button.dataset.name;
    search(button.dataset.name);
  });
});

searchInput.addEventListener("input", updateButtons);


/* ---------- Follow-up questions ---------- */

async function askQuestion(question) {
  isBusy = true;
  questionInput.value = "";
  updateButtons();
  hideMessage(questionError);

  // Show the question straight away, with a waiting message for the answer.
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

  try {
    const data = await postJson("/api/medications/ask", {
      medication: currentMedication,
      question: question,
    });
    answerText.textContent = data.answer;
    answerText.classList.remove("is-loading");
  } catch (error) {
    item.remove();
    questionInput.value = question; // put it back so it can be sent again
    showMessage(questionError, error.message);
  } finally {
    isBusy = false;
    updateButtons();
    questionInput.focus();
  }
}

questionForm.addEventListener("submit", function (event) {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (question !== "" && !isBusy && currentMedication) {
    askQuestion(question);
  }
});

questionInput.addEventListener("input", updateButtons);

updateButtons();
