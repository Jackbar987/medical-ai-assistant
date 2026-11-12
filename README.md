# PlainMed: AI Medical Information Assistant

A hackathon web application that explains health information in plain
language. It will have three tools:

1. **Symptom Assistant**: describe symptoms and get general educational information.
2. **Medical Document Explainer**: upload a lab report (PDF) and get it explained.
3. **Medication Assistant**: look up a medication's uses, side effects and precautions.

"PlainMed" is a placeholder name. To rename the app, change `APP_NAME` in
`app.py` and the title of this file.

> **Important:** this is an educational prototype. It does not diagnose,
> treat, or replace a doctor, pharmacist, or emergency services. It has not
> been clinically validated and it is not HIPAA-compliant. Use made-up
> examples only, never real patient records.

## Current status

**Phase 1 (environment setup) is in place.** The site runs locally and has a
homepage, a navigation bar, and one placeholder page for each tool. No AI is
connected yet.

| Phase | What gets built | Status |
|-------|-----------------|--------|
| 1 | Project setup, Flask app, homepage, navigation | Done |
| 2 | Chat, upload and search interfaces (no AI yet) | Next |
| 3 | AI connection and the Symptom Assistant | Planned |
| 4 | Document Explainer (PDF upload and explanation) | Planned |
| 5 | Medication Assistant with trusted sources | Planned |
| 6 | Testing and polish | Planned |

## How the pieces fit together

A web application has two halves:

- **The frontend** is what runs in the visitor's browser: HTML (the content),
  CSS (the appearance) and JavaScript (the behaviour).
- **The backend** is a program running on a server. Ours is written in Python
  with a framework called Flask. It decides what to send to the browser, and
  later it will talk to the AI service and read uploaded PDFs.

When you open `http://127.0.0.1:5000/symptoms`, this happens:

1. The browser sends a **request** for `/symptoms` to our Flask server.
2. Flask finds the matching **route** in `app.py` and runs its function.
3. That function fills in an HTML **template** and sends it back as the **response**.
4. The browser reads the HTML, then requests the CSS, JavaScript and font files it mentions.
5. The browser draws the finished page.

`127.0.0.1` means "this computer", so while developing, your own machine is
both the server and the visitor.

## What you need installed

- **Python 3.10 or newer**: https://www.python.org/downloads/
  (On Windows, tick "Add python.exe to PATH" in the installer.)
- **Git**: https://git-scm.com/downloads
- **A code editor**, for example Visual Studio Code: https://code.visualstudio.com/

Check Python and Git by opening a terminal and running:

```
python --version
git --version
```

On macOS and Linux the command may be `python3` instead of `python`.

## Run the app on your computer

Run these commands in a terminal, one line at a time.

**1. Download the project** (replace `YOUR-USERNAME`):

```
git clone https://github.com/YOUR-USERNAME/medical-ai-assistant.git
cd medical-ai-assistant
```

**2. Create a virtual environment.** This is a private folder of Python
packages for this project only, so it cannot clash with other projects.

```
python -m venv venv
```

**3. Activate it.** You need to do this each time you open a new terminal.

- Windows (PowerShell): `venv\Scripts\Activate.ps1`
- Windows (Command Prompt): `venv\Scripts\activate.bat`
- macOS / Linux: `source venv/bin/activate`

Your prompt should now start with `(venv)`.

**4. Install the packages the project needs:**

```
pip install -r requirements.txt
```

**5. Create your private settings file** by copying the example:

- Windows: `copy .env.example .env`
- macOS / Linux: `cp .env.example .env`

**6. Start the server:**

```
python app.py
```

**7. Open http://127.0.0.1:5000 in your browser.** You should see the
homepage. Press `Ctrl + C` in the terminal to stop the server.

### If something goes wrong

| Problem | Likely fix |
|---------|-----------|
| `python` is not recognised | Try `python3`, or reinstall Python with "Add to PATH" ticked. |
| `No module named flask` | The virtual environment is not active. Repeat step 3, then step 4. |
| "Address already in use" or a blank page on a Mac | Another program is using port 5000 (on macOS this is often AirPlay Receiver). Set `PORT=5001` in `.env` and open http://127.0.0.1:5001 instead. |
| PowerShell refuses to run `Activate.ps1` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again. |
| Changes to a file do not show up | Make sure `.env` contains `FLASK_DEBUG=1`, restart the server, and refresh the browser. |

## Project structure

```
medical-ai-assistant/
├── app.py                  The Flask app: starts the server and defines the page routes
├── requirements.txt        The Python packages to install
├── .env.example            Template for private settings (placeholders only)
├── .gitignore              Files Git must never upload, such as .env
├── README.md               This file
├── LICENSE                 The MIT License: the terms under which others may use the code
│
├── backend/                Python code behind each feature (placeholders for now)
│   ├── __init__.py             Marks the folder as a Python package
│   ├── ai_service.py           The one place that talks to the AI provider (Phase 3)
│   ├── safety.py               Shared safety rules and disclaimers (Phase 3)
│   ├── symptom_assistant.py    Symptom Assistant logic (Phase 3)
│   ├── document_explainer.py   PDF checking and text extraction (Phase 4)
│   └── medication_assistant.py Medication lookup (Phase 5)
│
├── templates/              HTML pages, filled in by Flask
│   ├── base.html               Shared layout: navigation, disclaimer, footer
│   ├── index.html              Homepage
│   ├── symptoms.html           Symptom Assistant page
│   ├── documents.html          Document Explainer page
│   └── medications.html        Medication Assistant page
│
├── static/                 Files sent to the browser unchanged
│   ├── css/style.css           All the styling
│   ├── js/main.js              Shared JavaScript (the mobile menu)
│   ├── fonts/                  The typeface, bundled with the project
│   └── images/favicon.svg      The icon in the browser tab
│
└── uploads/                Temporary home for uploaded PDFs (contents are never committed)
```

Two things differ from the first sketch of the structure:

- **`templates/base.html` was added.** It holds the navigation, disclaimer and
  footer once, and the other four pages build on it. Without it we would copy
  the same navigation into four files and have to update all four on every
  change.
- **`static/js/symptoms.js`, `documents.js` and `medications.js` are not
  created yet.** They arrive in Phase 2, when those pages have something
  interactive to control.

## Keeping secrets safe

- Real API keys go in `.env`, which only exists on your own computer.
- `.env` is listed in `.gitignore`, so Git will not upload it.
- `.env.example` is uploaded, so it must only ever contain placeholders.
- API keys are only ever used by the Python backend. They never go in HTML,
  CSS or JavaScript, because visitors can read all of those.

If a key is ever committed by accident, deleting it in a later commit is not
enough, because Git keeps history. Cancel (revoke) the key with the provider
and create a new one.

## Working as a team with Git

```
git pull                      Get your teammates' latest changes
git status                    See which files you changed
git add .                     Choose all changes for the next commit
git commit -m "Describe it"   Save a snapshot with a message
git push                      Upload your commits to GitHub
```

Run `git pull` before you start working, and commit small, working steps.

## License and credits

The project's code is released under the MIT License (see `LICENSE`).

The typeface is Atkinson Hyperlegible Next, used under the SIL Open Font
License. The licence text is in `static/fonts/LICENSE.txt`.
