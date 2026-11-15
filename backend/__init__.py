"""
The backend package: the Python code behind each feature.

The empty-looking __init__.py file tells Python that this folder is a
"package", so app.py can import from it, for example:

    from backend.symptom_assistant import ...

Modules:
    ai_service.py            the one place that talks to the AI (Claude)
    safety.py                safety rules for the AI and the emergency check
    rate_limit.py            limits how many AI requests one visitor can make
    symptom_assistant.py     the Symptom Assistant
    document_explainer.py    the Medical Document Explainer
    medication_assistant.py  the Medication Assistant
"""
