"""Small session-based CSRF protection.

How it works (the "matching ticket stub" idea):
1. When a page renders a form, ``csrf_token()`` creates a random token and
   keeps one copy in the signed session cookie.
2. The form sends the same token back in a hidden ``csrf_token`` field
   (or JavaScript sends it in the ``X-CSRF-Token`` header).
3. Before any state-changing request, ``protect_state_changes`` compares the
   two copies. A different website cannot read the token, so it cannot forge
   a valid request.
"""

from __future__ import annotations

import secrets

from flask import current_app, request, session
from werkzeug.exceptions import BadRequest

SESSION_KEY = "csrf_token"
FORM_FIELD = "csrf_token"
HEADER_NAME = "X-CSRF-Token"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class CSRFError(BadRequest):
    """Raised when a state-changing request has a missing or wrong token."""

    description = "Invalid CSRF token."


def get_csrf_token() -> str:
    """Return this session's token, creating it on first use."""

    token = session.get(SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[SESSION_KEY] = token
    return token


def protect_state_changes() -> None:
    """Reject unsafe requests whose token does not match the session token."""

    if request.method not in UNSAFE_METHODS or not current_app.config.get("CSRF_ENABLED", True):
        return
    expected = session.get(SESSION_KEY)
    submitted = request.headers.get(HEADER_NAME) or request.form.get(FORM_FIELD)
    if not expected or not submitted or not secrets.compare_digest(str(submitted), str(expected)):
        raise CSRFError()
