"""Sign-in and role checks for every request (the "reception desk").

``require_login`` runs before every request:
1. Public pages (sign-in, first-time setup, CSS/JS) are always allowed.
2. Everyone else must be signed in; otherwise they are sent to the sign-in
   page (or get a 401 JSON reply from JavaScript requests).
3. A session idle for too long, or older than the maximum lifetime, ends.
4. Kiosk accounts may only use the face check-in page.
"""

from __future__ import annotations

import time

from flask import current_app, flash, g, jsonify, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models.user import ROLE_KIOSK, User

SESSION_USER_ID = "user_id"
SESSION_LOGIN_AT = "login_at"
SESSION_LAST_SEEN = "last_seen"

PUBLIC_ENDPOINTS = frozenset({"auth.login", "auth.setup", "static"})
# Everything a kiosk screen may do. Everything else needs an administrator.
KIOSK_ENDPOINTS = frozenset({"recognition.index", "recognition.check_in_capture", "auth.logout"})


def _wants_json() -> bool:
    return request.accept_mimetypes.best == "application/json"


def sign_in(user: User) -> None:
    """Start a fresh session for ``user``.

    ``session.clear()`` first discards anything from before sign-in (including
    the old CSRF token), so a session prepared by an attacker can never become
    a signed-in session ("session fixation").
    """

    session.clear()
    now = int(time.time())
    session[SESSION_USER_ID] = user.id
    session[SESSION_LOGIN_AT] = now
    session[SESSION_LAST_SEEN] = now


def sign_out() -> None:
    session.clear()


def _idle_limit_seconds(user: User) -> int:
    key = "KIOSK_SESSION_IDLE_MINUTES" if user.role == ROLE_KIOSK else "SESSION_IDLE_MINUTES"
    return int(current_app.config[key]) * 60


def _session_user() -> User | None:
    user_id = session.get(SESSION_USER_ID)
    if user_id is None:
        return None
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:  # deleted or disabled since sign-in: takes effect immediately
        sign_out()
        return None

    now = int(time.time())
    max_age = int(current_app.config["SESSION_MAX_HOURS"]) * 3600
    idle = now - int(session.get(SESSION_LAST_SEEN, 0))
    if idle > _idle_limit_seconds(user) or now - int(session.get(SESSION_LOGIN_AT, 0)) > max_age:
        sign_out()
        g.session_expired = True
        return None
    session[SESSION_LAST_SEEN] = now
    return user


def _not_signed_in():
    message = "Your session has expired. Please sign in again." if g.get("session_expired") else "Please sign in."
    if _wants_json() or request.method != "GET":
        return jsonify(error=f"{message} Reload the page."), 401
    if g.get("session_expired"):
        flash(message, "warning")
    return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))


def require_login():
    g.user = None
    if request.endpoint in PUBLIC_ENDPOINTS:
        g.user = _session_user()  # lets the sign-in page notice an existing session
        return None

    user = _session_user()
    if user is None:
        return _not_signed_in()
    g.user = user

    if user.role == ROLE_KIOSK and request.endpoint not in KIOSK_ENDPOINTS:
        if request.method == "GET" and not _wants_json():
            return redirect(url_for("recognition.index"))
        message = "Kiosk accounts can only use face check-in."
        if _wants_json():
            return jsonify(error=message), 403
        return render_template("error.html", title="Not allowed", message=message), 403
    return None


def current_user() -> User | None:
    return g.get("user")
