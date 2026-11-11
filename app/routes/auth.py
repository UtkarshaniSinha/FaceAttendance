"""Sign-in, sign-out, first-time setup and user management (admins only)."""

from __future__ import annotations

from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import Forbidden, NotFound

from app.auth import sign_in, sign_out
from app.extensions import db
from app.models.user import ROLE_ADMIN, ROLE_KIOSK, ROLES, User
from app.services.user_service import (
    UserValidationError,
    authenticate,
    create_user,
    deactivate_user,
    list_users,
    reactivate_user,
    unlock_user,
    user_count,
)

auth_bp = Blueprint("auth", __name__)

LOCAL_ADDRESSES = frozenset({"127.0.0.1", "::1"})


def _home_for(user: User) -> str:
    return url_for("recognition.index") if user.role == ROLE_KIOSK else url_for("main.dashboard")


def _safe_next(target: str | None) -> str | None:
    """Only follow ``?next=`` to a page on THIS site (blocks "open redirects")."""

    if not target or "\\" in target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if user_count() == 0:
        return redirect(url_for("auth.setup"))
    if g.user is not None:
        return redirect(_home_for(g.user))

    if request.method == "POST":
        result = authenticate(request.form.get("username"), request.form.get("password"), current_app.config)
        if result.user is None:
            # Username only, never the password. Helps spot guessing in the log.
            current_app.logger.warning("Failed sign-in for username %r", (request.form.get("username") or "")[:32])
            flash(result.error, "error")
            return render_template("auth/login.html"), 401
        sign_in(result.user)
        current_app.logger.info("User %s signed in", result.user.username)
        next_page = _safe_next(request.args.get("next"))
        if result.user.role == ROLE_KIOSK:
            next_page = None  # kiosks always start at check-in
        return redirect(next_page or _home_for(result.user))
    return render_template("auth/login.html")


@auth_bp.post("/logout")
def logout():
    sign_out()
    flash("You have signed out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/setup", methods=["GET", "POST"])
def setup():
    """Create the first administrator. Disappears once any user exists."""

    if user_count() > 0:
        return redirect(url_for("auth.login"))
    if request.remote_addr not in LOCAL_ADDRESSES:
        raise Forbidden("First-time setup is only allowed from this computer.")
    if request.method == "POST":
        try:
            user = create_user(
                request.form.get("username"),
                request.form.get("password"),
                request.form.get("confirm_password"),
                ROLE_ADMIN,
                current_app.config,
            )
        except UserValidationError as error:
            flash(str(error), "error")
        else:
            sign_in(user)
            flash("Administrator account created. You are signed in.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth/setup.html")


# ---- user management (admin only: the access gate blocks kiosks) ----

def _user_or_404(user_id: int) -> User:
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFound("User not found.")
    return user


@auth_bp.get("/users")
def users():
    return render_template("auth/users.html", users=list_users())


@auth_bp.route("/users/new", methods=["GET", "POST"])
def create_user_view():
    if request.method == "POST":
        try:
            user = create_user(
                request.form.get("username"),
                request.form.get("password"),
                request.form.get("confirm_password"),
                request.form.get("role"),
                current_app.config,
            )
        except UserValidationError as error:
            flash(str(error), "error")
        else:
            flash(f"User {user.username} ({user.role}) was created.", "success")
            return redirect(url_for("auth.users"))
    return render_template("auth/user_form.html", roles=ROLES)


@auth_bp.post("/users/<int:user_id>/deactivate")
def deactivate(user_id: int):
    user = _user_or_404(user_id)
    try:
        deactivate_user(user, g.user)
    except UserValidationError as error:
        flash(str(error), "error")
    else:
        flash(f"{user.username} was disabled and signed out.", "success")
    return redirect(url_for("auth.users"))


@auth_bp.post("/users/<int:user_id>/reactivate")
def reactivate(user_id: int):
    user = _user_or_404(user_id)
    reactivate_user(user)
    flash(f"{user.username} was enabled.", "success")
    return redirect(url_for("auth.users"))


@auth_bp.post("/users/<int:user_id>/unlock")
def unlock(user_id: int):
    user = _user_or_404(user_id)
    unlock_user(user)
    flash(f"{user.username} was unlocked.", "success")
    return redirect(url_for("auth.users"))
