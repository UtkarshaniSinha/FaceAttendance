"""Creating users, checking passwords and locking accounts after failed attempts."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping

from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.user import ROLE_ADMIN, ROLES, User, as_utc

USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,32}$")
MAX_PASSWORD_LENGTH = 128
GENERIC_LOGIN_ERROR = "Incorrect username or password."

# Checked against when the username does not exist, so a wrong username takes
# as long as a wrong password. Otherwise response time would reveal which
# usernames exist ("timing attack").
_DUMMY_HASH = generate_password_hash("not-a-real-password-just-for-equal-timing")


class UserValidationError(ValueError):
    """A user-safe reason why a user could not be created or changed."""


@dataclass(frozen=True)
class LoginResult:
    user: User | None
    error: str | None = None


def user_count() -> int:
    return db.session.scalar(select(func.count()).select_from(User)) or 0


def active_admin_count() -> int:
    return db.session.scalar(
        select(func.count()).select_from(User).where(User.role == ROLE_ADMIN, User.is_active.is_(True))
    ) or 0


def list_users() -> list[User]:
    return list(db.session.scalars(select(User).order_by(User.username)))


def find_user(username: str) -> User | None:
    return db.session.scalar(select(User).where(User.username == username.strip().lower()))


def validate_password(password: str, username: str, minimum_length: int) -> None:
    if len(password) < minimum_length:
        raise UserValidationError(f"The password must be at least {minimum_length} characters long.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise UserValidationError(f"The password must be at most {MAX_PASSWORD_LENGTH} characters long.")
    if username and username in password.lower():
        raise UserValidationError("The password must not contain the username.")


def create_user(username: str | None, password: str | None, confirm: str | None, role: str | None,
                config: Mapping[str, object]) -> User:
    username = (username or "").strip().lower()
    password = password or ""
    if not USERNAME_PATTERN.fullmatch(username):
        raise UserValidationError(
            "The username must be 3–32 characters: lowercase letters, digits, dot, dash or underscore."
        )
    if role not in ROLES:
        raise UserValidationError("Choose a valid role.")
    if password != (confirm or ""):
        raise UserValidationError("The two passwords do not match.")
    validate_password(password, username, int(config["PASSWORD_MIN_LENGTH"]))
    if find_user(username) is not None:
        raise UserValidationError("That username is already taken.")

    user = User(username=username, password_hash=generate_password_hash(password), role=role)
    db.session.add(user)
    db.session.commit()
    return user


def set_password(user: User, password: str, config: Mapping[str, object]) -> None:
    validate_password(password, user.username, int(config["PASSWORD_MIN_LENGTH"]))
    user.password_hash = generate_password_hash(password)
    user.failed_login_count = 0
    user.locked_until = None
    db.session.commit()


def authenticate(username: str | None, password: str | None, config: Mapping[str, object]) -> LoginResult:
    """Check a username and password, counting failures and locking the account.

    After LOGIN_MAX_ATTEMPTS wrong passwords in a row the account is locked for
    LOGIN_LOCKOUT_MINUTES. While locked, even the correct password is refused,
    so an attacker cannot keep guessing.
    """

    now = datetime.now(timezone.utc)
    user = find_user(username or "")
    if user is None:
        check_password_hash(_DUMMY_HASH, password or "")  # equal timing, result ignored
        return LoginResult(None, GENERIC_LOGIN_ERROR)

    if user.locked_now(now):
        minutes = math.ceil((as_utc(user.locked_until) - now).total_seconds() / 60)
        return LoginResult(None, f"Too many failed attempts. This account is locked for {minutes} more minute(s).")

    if not check_password_hash(user.password_hash, password or ""):
        user.failed_login_count += 1
        if user.failed_login_count >= int(config["LOGIN_MAX_ATTEMPTS"]):
            user.locked_until = now + timedelta(minutes=int(config["LOGIN_LOCKOUT_MINUTES"]))
            user.failed_login_count = 0
            db.session.commit()
            return LoginResult(None, "Too many failed attempts. This account is now locked for "
                                     f"{int(config['LOGIN_LOCKOUT_MINUTES'])} minutes.")
        db.session.commit()
        return LoginResult(None, GENERIC_LOGIN_ERROR)

    if not user.is_active:  # checked after the password: does not reveal disabled accounts to guessers
        return LoginResult(None, "This account is disabled. Ask an administrator.")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    db.session.commit()
    return LoginResult(user)


def deactivate_user(user: User, acting_user: User) -> None:
    if user.id == acting_user.id:
        raise UserValidationError("You cannot disable your own account.")
    if user.is_admin and user.is_active and active_admin_count() <= 1:
        raise UserValidationError("At least one active administrator must remain.")
    user.is_active = False
    db.session.commit()


def reactivate_user(user: User) -> None:
    user.is_active = True
    db.session.commit()


def unlock_user(user: User) -> None:
    user.failed_login_count = 0
    user.locked_until = None
    db.session.commit()
