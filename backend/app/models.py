"""SQLAlchemy 2.0 ORM models.

Schedule content is bilingual: every visitor-facing string exists in English and
Spanish so the site can switch language without a round trip to a translation
service. Day-of-week integers follow JavaScript convention (0 = Sunday).
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="admin", cascade="all, delete-orphan"
    )


class Session(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("admins.id"), nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    admin: Mapped["Admin"] = relationship(back_populates="sessions")


class Event(Base):
    """One row per weekday: what is on, described in both languages.

    Times deliberately live in :class:`Hours` instead, so an event and its
    opening hours are edited together from one place in the admin panel.
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    title_en: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title_es: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    note_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    note_es: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Hours(Base):
    """Opening/closing times for a weekday. Not language-dependent."""

    __tablename__ = "hours"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    open_time: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    close_time: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ClosedDay(Base):
    """A one-off closure (holiday, private booking) with a bilingual reason."""

    __tablename__ = "closed_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)  # YYYY-MM-DD
    reason_en: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    reason_es: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )