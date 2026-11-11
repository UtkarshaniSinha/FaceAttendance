"""App user accounts: the people (or kiosk screens) allowed to use the app.

These are NOT employees. An employee is someone whose attendance is tracked;
a user is someone who signs in to operate the app. Two roles:

* admin : manages employees, enrolment, consent, users and check-in.
* kiosk : can only open the face check-in page (for a shared screen at the door).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

ROLE_ADMIN = "admin"
ROLE_KIOSK = "kiosk"
ROLES = (ROLE_ADMIN, ROLE_KIOSK)


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite returns stored UTC times without tzinfo; mark them as UTC again."""

    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'kiosk')", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    # Only a salted, slow hash (scrypt) is stored, never the password itself.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default=ROLE_ADMIN)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    def locked_now(self, now: datetime | None = None) -> bool:
        locked_until = as_utc(self.locked_until)
        return locked_until is not None and locked_until > (now or datetime.now(timezone.utc))

    def __repr__(self) -> str:  # never include the password hash
        return f"<User {self.username} ({self.role})>"
