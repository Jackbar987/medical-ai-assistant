"""
app.py - the entry point of our web application.

This file creates the Flask app and defines its "routes". A route connects a
web address (like /symptoms) to a Python function that decides what to send
back to the browser.

Run it from the project folder with:

    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from backend import symptom_assistant

# Read settings from a file named .env (if it exists) and make them available
# through os.getenv(). The .env file holds private values such as API keys,
# and it is never committed to GitHub. See .env.example for the format.
load_dotenv()

# Create the Flask application. Flask automatically looks for HTML files in
# the "templates" folder and for CSS, JavaScript, fonts and images in the
# "static" folder.
app = Flask(__name__)

# The name shown in the navigation bar and in browser tabs.
# Change it here and it changes on every page.
APP_NAME = "PlainMed"


@app.context_processor
def inject_app_name():
    """Make app_name available inside every HTML template."""
    return {"app_name": APP_NAME}


# ---------------------------------------------------------------------------
# Page routes
#
# Each function below runs when someone visits the address in @app.route().
# render_template() fills in an HTML file from the templates folder and sends
# the finished page back to the browser.
# ---------------------------------------------------------------------------


@app.route("/")
def home():
    """Homepage: introduces the app and links to the three tools."""
    return render_template("index.html")


@app.route("/symptoms")
def symptoms():
    """Symptom Assistant page (the chat is added in Phases 2 and 3)."""
    return render_template("symptoms.html")


@app.route("/documents")
def documents():
    """Document Explainer page (the PDF upload is added in Phases 2 and 4)."""
    return render_template("documents.html")


@app.route("/medications")
def medications():
    """Medication Assistant page (the search is added in Phases 2 and 5)."""
    return render_template("medications.html")


# ---------------------------------------------------------------------------
# API routes
#
# Page routes send back HTML for people to look at. API routes send back
# JSON: plain data that our JavaScript reads and then displays.
#
# methods=["POST"] means this route only accepts POST requests, the kind a
# browser uses to SEND data. Visiting the address directly (a GET request)
# returns "405 Method Not Allowed".
# ---------------------------------------------------------------------------


@app.route("/api/symptoms", methods=["POST"])
def symptoms_api():
    """Receive the chat conversation and return the assistant's reply."""
    # get_json() turns the JSON text sent by symptoms.js into Python data.
    # silent=True gives us None instead of crashing if the body isn't JSON.
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="The request could not be read. Reload the page and try again."), 400

    messages = data.get("messages")
    error = symptom_assistant.validate_conversation(messages)
    if error:
        # 400 means "Bad Request": the problem is with what was sent.
        return jsonify(error=error), 400

    reply = symptom_assistant.get_reply(messages)
    return jsonify(reply=reply)


# This block only runs when we start the file directly with "python app.py".
if __name__ == "__main__":
    # Debug mode restarts the server whenever we save a file and shows
    # detailed error pages. It is helpful while developing but unsafe on a
    # public website, so it stays off unless .env contains FLASK_DEBUG=1.
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=debug_mode, port=port)
