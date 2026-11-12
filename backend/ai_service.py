"""
ai_service.py - the one place that talks to the AI provider's API.

Planned for Phase 3.

Every feature sends its AI requests through this module. Keeping that code in
one file means the API key is read in one place, errors are handled in one
place, and switching AI providers later only requires changes here.
"""
