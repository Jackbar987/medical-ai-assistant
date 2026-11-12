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
from flask import Flask, render_template

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


# This block only runs when we start the file directly with "python app.py".
if __name__ == "__main__":
    # Debug mode restarts the server whenever we save a file and shows
    # detailed error pages. It is helpful while developing but unsafe on a
    # public website, so it stays off unless .env contains FLASK_DEBUG=1.
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=debug_mode, port=port)
