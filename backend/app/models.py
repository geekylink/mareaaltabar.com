"""SQLAlchemy 2.0 ORM models.

Schedule and menu content is bilingual: every visitor-facing string exists in
English and Spanish so the site can switch language without a round trip to a
translation service. Day-of-week integers follow JavaScript convention
(0 = Sunday).
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


class MenuCategory(Base):
    """One group of drinks — Beer, Wine, Cocktails — in both languages.

    Categories are rows rather than a code constant so the bar can add a section
    (a food menu, a happy-hour list) from the admin panel without a deploy.
    ``slug`` is the anchor id on the public menu page and is unique.
    """

    __tablename__ = "menu_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, default="")
    name_en: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    name_es: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Cleared rather than deleted when a section is off for the season, so the
    # drinks in it survive and come back when it returns.
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["MenuItem"]] = relationship(
        back_populates="category", cascade="all, delete-orphan", order_by="MenuItem.sort_order"
    )


class MenuItem(Base):
    """One drink, described in both languages.

    ``price`` is the headline figure exactly as the bar types it ("2.50"), with
    any multi-buy offers living in :class:`MenuItemPromo` beneath it rather than
    crammed into the same string. ``ingredients_*`` carry a comma-separated list,
    which is what the cocktails section shows; every other category can leave them
    blank. All fields are optional except the names, so a half-entered drink still
    renders.
    """

    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("menu_categories.id", ondelete="CASCADE"), nullable=False
    )

    name_en: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    name_es: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    description_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description_es: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ingredients_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ingredients_es: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Text, not a number: it is a displayed price, never a quantity we calculate
    # with, so storing it verbatim avoids float rounding and locale surprises.
    price: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    category: Mapped["MenuCategory"] = relationship(back_populates="items")
    promos: Mapped[list["MenuItemPromo"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="MenuItemPromo.sort_order"
    )


class MenuItemPromo(Base):
    """A multi-buy or bundle offer shown under a drink's headline price.

    Several can exist per item ("6x $7.00" and "case $12.00"), so this is a table
    rather than a column. The label is bilingual because the price formatting is
    the only part that is language-neutral — "6 por $7.00" is not "6x $7.00".
    """

    __tablename__ = "menu_item_promos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False
    )
    label_en: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    label_es: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    item: Mapped["MenuItem"] = relationship(back_populates="promos")


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