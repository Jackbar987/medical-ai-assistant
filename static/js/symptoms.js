/*
  symptoms.js - makes the Symptom Assistant chat work.

  What happens when someone presses Send:

    1. We add their message to the page and to the `conversation` list.
    2. We send the whole conversation to our Flask server at /api/symptoms.
    3. While we wait, a "writing a reply" indicator is shown.
    4. The server answers with JSON: either { "reply": "..." } or { "error": "..." }.
    5. We show the reply, or show the error and put the message back in the box.

  The conversation is only kept in this page's memory. Reloading the page or
  pressing "Clear conversation" erases it, and nothing is saved anywhere.
*/

// Must match MAX_USER_MESSAGE_LENGTH in backend/symptom_assistant.py.
const MAX_LENGTH = 2000;

// Every message so far, in order. Each one looks like:
//   { role: "user", content: "..." }  or  { role: "assistant", content: "..." }
const conversation = [];

// True while we are waiting for the server, so people can't send twice.
let isWaiting = false;

// Find the parts of the page we need to work with.
const chatLog = document.getElementById("chat-log");
const emptyState = document.getElementById("chat-empty");
const errorBox = document.getElementById("chat-error");
const form = document.getElementById("chat-form");
const input = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const clearButton = document.getElementById("clear-button");
const counter = document.getElementById("chat-count");


/* ---------- Showing things on the page ---------- */

// Add one message bubble to the chat and return it.
function addMessage(role, text) {
  emptyState.hidden = true;

  const bubble = document.createElement("div");
  bubble.className = "message message-" + role;

  // Hidden label so screen reader users know who said what.
  const label = document.createElement("span");
  label.className = "visually-hidden";
  label.textContent = role === "user" ? "You said: " : "PlainMed replied: ";

  const body = document.createElement("p");
  // IMPORTANT: always use textContent, never innerHTML, for message text.
  // textContent shows text exactly as written. innerHTML would run any HTML
  // hidden in a message, which attackers can use to inject harmful code.
  body.textContent = text;

  bubble.append(label, body);
  chatLog.appendChild(bubble);
  scrollToBottom();
  return bubble;
}

// The animated dots shown while waiting for a reply.
let loadingBubble = null;

function showLoading() {
  loadingBubble = document.createElement("div");
  loadingBubble.className = "message message-assistant message-loading";
  loadingBubble.innerHTML =
    '<span class="visually-hidden">PlainMed is writing a reply</span>' +
    '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  chatLog.appendChild(loadingBubble);
  scrollToBottom();
}

function hideLoading() {
  if (loadingBubble) {
    loadingBubble.remove();
    loadingBubble = null;
  }
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function hideError() {
  errorBox.textContent = "";
  errorBox.hidden = true;
}

function scrollToBottom() {
  chatLog.scrollTop = chatLog.scrollHeight;
}

// Turn buttons on or off and update the character counter.
function updateControls() {
  const length = input.value.length;
  counter.textContent = length + " / " + MAX_LENGTH;
  counter.classList.toggle("is-near-limit", length > MAX_LENGTH * 0.9);

  sendButton.disabled = isWaiting || input.value.trim() === "";
  clearButton.disabled = isWaiting || conversation.length === 0;
}


/* ---------- Talking to the server ---------- */

// "async" lets this function wait for the server with "await" while the rest
// of the page keeps working, so the page doesn't freeze.
async function sendMessage(text) {
  conversation.push({ role: "user", content: text });
  const userBubble = addMessage("user", text);

  input.value = "";
  isWaiting = true;
  hideError();
  updateControls();
  showLoading();

  try {
    // fetch() sends an HTTP request to our Flask server.
    const response = await fetch("/api/symptoms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // JSON.stringify turns our JavaScript list into JSON text.
      body: JSON.stringify({ messages: conversation }),
    });

    // Read the JSON the server sent back. If the server crashed, it may send
    // an HTML error page instead of JSON, so reading can fail: in that case
    // we treat data as empty and show a general error below.
    let data = null;
    try {
      data = await response.json();
    } catch (readError) {
      data = null;
    }

    // response.ok is true for success codes (200-299).
    if (!response.ok || !data || typeof data.reply !== "string") {
      throw new Error(
        (data && data.error) || "Something went wrong on the server. Wait a moment and send again."
      );
    }

    conversation.push({ role: "assistant", content: data.reply });
    hideLoading();
    addMessage("assistant", data.reply);
  } catch (error) {
    hideLoading();

    // Undo the failed message so the conversation stays consistent, and put
    // the text back in the box so it can be sent again without retyping.
    conversation.pop();
    userBubble.remove();
    if (conversation.length === 0) {
      emptyState.hidden = false;
    }
    input.value = text;

    // fetch() throws a TypeError when the request never reached the server,
    // for example when the internet connection is down.
    if (error instanceof TypeError) {
      showError("Couldn't reach the server. Check your internet connection and send again.");
    } else {
      showError(error.message);
    }
  } finally {
    // "finally" runs whether the request worked or failed.
    isWaiting = false;
    updateControls();
    input.focus();
  }
}


/* ---------- Reacting to what the user does ---------- */

// Pressing Send (or Enter) submits the form.
form.addEventListener("submit", function (event) {
  // Stop the browser's default form behaviour, which reloads the page.
  event.preventDefault();

  const text = input.value.trim();
  if (text === "" || isWaiting) {
    return;
  }
  sendMessage(text);
});

// Enter sends; Shift + Enter adds a new line.
input.addEventListener("keydown", function (event) {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});

// Keep the counter and Send button up to date while typing.
input.addEventListener("input", updateControls);

clearButton.addEventListener("click", function () {
  conversation.length = 0;
  chatLog.querySelectorAll(".message").forEach(function (bubble) {
    bubble.remove();
  });
  emptyState.hidden = false;
  hideError();
  updateControls();
  input.focus();
});

// Set the buttons correctly when the page first loads.
updateControls();
