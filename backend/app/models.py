"""SQLAlchemy 2.0 ORM models.

Schedule and menu content is bilingual: every visitor-facing string exists in
English and Spanish so the site can switch language without a round trip to a
translation service. Day-of-week integers follow JavaScript convention
(0 = Sunday).
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
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
    # At most one available drink carries this flag; the menu write handlers
    # clear it on every other row when it is set. The hero reads it rather than
    # storing the day's drink in code, so changing it is an admin edit.
    is_drink_of_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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

    An offer can also be a daily happy hour. ``days`` is a comma-separated list
    of weekday numbers (0 = Sunday); blank means every day. ``start_time`` and
    ``end_time`` are bar-local ``HH:MM``; an end before the start crosses
    midnight. ``starts_on`` and ``ends_on`` are ``YYYY-MM-DD`` bounds. Every
    blank window means "always", which is how promos entered before these
    columns existed keep working. ``is_active`` is the immediate off switch,
    separate from the schedule, so an offer can be paused and brought back
    unchanged.
    """

    __tablename__ = "menu_item_promos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False
    )
    label_en: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    label_es: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    days: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    start_time: Mapped[str] = mapped_column(String(5), nullable=False, default="")
    end_time: Mapped[str] = mapped_column(String(5), nullable=False, default="")
    starts_on: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    ends_on: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    item: Mapped["MenuItem"] = relationship(back_populates="promos")


class LoginAttempt(Base):
    """One row per login attempt, whatever the outcome.

    Written on every ``POST /admin/login`` — the success, the wrong password, the
    username that does not exist, and the attempts the rate limiter turned away —
    because spotting the attempts is the point, not just recording the successes.
    The username is whatever was typed, so a stranger guessing at names shows up
    here instead of leaving no trace at all.

    There is deliberately no password column, and no column one could go in: the
    submitted password is never handed to the logger, so it cannot land here even
    by accident. ``user_agent`` is kept for the same reason the IP is — to tell a
    real admin's browser apart from a script replaying their credentials.
    """

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    # success | invalid_credentials | rate_limited
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    user_agent: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditEntry(Base):
    """Who changed what, and what the row looked like beforehand.

    This is the answer to "who changed Friday's hours to 4pm, and when" — with two
    people editing the same week there is no other way to find out, and no way to
    spot an accidental edit afterwards. An entry is written in the same
    transaction as the change it describes, so a change can never exist without
    its log row.

    ``admin_username`` is a plain string rather than a foreign key on purpose:
    deleting an admin must not delete the record of what they did. ``details``
    carries the substance — for an update, only the fields that actually changed,
    as ``{"open_time": {"from": "16:00", "to": "18:00"}}``, so the log answers
    what changed instead of repeating the whole row on every save. For a create or
    a delete it is the row's own fields.

    Nothing in the application updates or deletes a row here; the only way out is
    the retention purge in :mod:`app.audit`.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # menu | schedule
    area: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    # create | update | delete
    action: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    admin_username: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    user_agent: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # A "<kind>:<id>" key — 'schedule_day:5', 'menu_item:41' — so the panel can
    # render the row in the language it is currently in.
    target: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # The row's own name, verbatim: admin-entered content, not UI text.
    target_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# Every read of these tables is "the newest N, of one area", which is the shape
# these indexes serve once the tables have filled up.
Index("ix_login_attempts_created", LoginAttempt.created_at)
Index("ix_audit_log_area_created", AuditEntry.area, AuditEntry.created_at)


class SpecialEvent(Base):
    """A dated, one-off event: "Friday the 26th — DJ Sol".

    ``events`` is the recurring weekly pattern; this is the exception to it. The
    date is an ISO ``YYYY-MM-DD`` string so it sorts and compares as text, as
    ``closed_days`` does. ``start_time`` and ``end_time`` are bar-local ``HH:MM``
    and optional: a blank pair means "during opening hours". ``image_url`` is a
    link rather than an upload because the upload pipeline is #50; it is
    restricted to http(s) and site-relative paths by the write schema.

    ``is_active`` is the immediate off switch, separate from the date, so an
    event can be hidden while it is being planned and brought back unchanged.
    """

    __tablename__ = "special_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, default="")  # YYYY-MM-DD
    title_en: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title_es: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description_es: Mapped[str] = mapped_column(Text, nullable=False, default="")
    start_time: Mapped[str] = mapped_column(String(5), nullable=False, default="")
    end_time: Mapped[str] = mapped_column(String(5), nullable=False, default="")
    image_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Deleting a dated event removes its guest list too. The FK is declared with
    # ON DELETE CASCADE as well, but the ORM cascade keeps the in-memory SQLite
    # test database honest even when PRAGMA foreign_keys is off.
    rsvps: Mapped[list["Rsvp"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


# The public read is "upcoming events, soonest first"; the admin read adds past
# and switched-off rows. This index serves the public query directly.
Index("ix_special_events_date_active", SpecialEvent.date, SpecialEvent.is_active)


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


class Notice(Base):
    """An emergency banner: a closure, a power cut, a last-minute change.

    The point is that the owner can publish one from the admin panel without a
    deploy, so it is a row rather than a template. ``message_*`` are bilingual
    as everywhere else. ``severity`` only chooses the banner's colour
    (``info``, ``warning`` or ``critical``); it carries no other behaviour.

    The time window is stored as bar-local ``YYYY-MM-DDTHH:MM`` strings, which
    compare correctly in SQL and need no timezone conversion at read time. A
    blank ``starts_at`` means "from now", and a blank ``ends_at`` means "until
    someone switches it off". ``is_active`` is the immediate off switch, separate
    from the window, so a notice can be paused and brought back unchanged.
    """

    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    message_es: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # info | warning | critical
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    starts_at: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    ends_at: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# The public read is "currently live notices, newest first", which is exactly
# what this index serves once a year of emergency banners has accumulated.
Index("ix_notices_active_created", Notice.is_active, Notice.created_at)


class Submission(Base):
    """One message from the public contact form.

    There is deliberately no email-delivery column or status: the shared admin
    inbox is the delivery mechanism (#15), and a message that has been read is
    still kept until an admin deletes it. ``ip`` and ``user_agent`` are stored
    for the same reason the login log stores them — to tell a real visitor apart
    from a script — but the public site never reads this table.

    ``name``, ``contact``, ``subject`` and ``message`` are sanitised before they
    are stored (see ``app.sanitize``), and every template renders them through
    Jinja autoescape or the panel's ``esc()``. The 1,000-character message cap is
    enforced by the request schema as well as the form.
    """

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    contact: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    subject: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    user_agent: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# The inbox asks for "unread first, then newest"; the badge asks for a count of
# unread rows. This index serves both without scanning the table.
Index("ix_submissions_unread_created", Submission.is_read, Submission.created_at)


class ContentSection(Base):
    """A named block of editable site content — a package list, an About box, a gallery.

    The section is the heading and the shared copy; its items are the rows the
    owner adds underneath it. Keeping both in the database means #19, #20, #22
    and #8 can be filled in from the panel instead of from a deploy. The slug is
    what a future public component (or a link) uses to ask for one section.
    """

    __tablename__ = "content_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, default="")
    title_en: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title_es: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    body_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_es: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["ContentItem"]] = relationship(
        back_populates="section", cascade="all, delete-orphan", order_by="ContentItem.sort_order"
    )


class ContentItem(Base):
    """One row inside a :class:`ContentSection`.

    ``price`` is text for the same reason a menu price is: it is displayed, never
    calculated with. ``starts_on`` / ``ends_on`` are optional ISO dates, inclusive;
    both blank means the item is permanent. ``image_url`` is a link rather than an
    upload because #50 is not built, and is restricted by the write schema.
    """

    __tablename__ = "content_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("content_sections.id", ondelete="CASCADE"), nullable=False
    )
    title_en: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title_es: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    body_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_es: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    image_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    starts_on: Mapped[str] = mapped_column(String(10), nullable=False, default="")  # YYYY-MM-DD
    ends_on: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    section: Mapped["ContentSection"] = relationship(back_populates="items")


# The public read is "active sections in order"; the panel and the API also ask
# for one section's items, which the cascade index already serves.
Index("ix_content_sections_active_order", ContentSection.is_active, ContentSection.sort_order)
Index("ix_content_items_section_order", ContentItem.section_id, ContentItem.sort_order)


class BlogPost(Base):
    """One news article (ticket #24).

    A post is deliberately not a generic :class:`ContentSection` row: it has a
    public URL of its own (``/news/<slug>``), a publication date that controls
    when it becomes visible, and SEO fields (excerpt, image) that a package or
    gallery row does not need. Keeping those first-class is what makes the page
    shareable from Instagram and indexable on its own.

    ``body_en`` / ``body_es`` are plain text. Blank lines separate paragraphs,
    which both the server-rendered article and ``BlogPost.svelte`` honour; HTML
    is never stored, so an admin cannot accidentally break the page.
    """

    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, default="")
    title_en: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title_es: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    excerpt_en: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    excerpt_es: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    body_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_es: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    published_on: Mapped[str] = mapped_column(String(10), nullable=False, default="")  # YYYY-MM-DD
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# The public list is "active posts published by today, newest first"; the admin
# list is "newest first, every row". This index serves the public read and keeps
# the admin sort cheap.
Index("ix_blog_posts_active_published", BlogPost.is_active, BlogPost.published_on)


class Subscriber(Base):
    """One newsletter signup from the public site.

    ``email`` is stored lower-cased and unique, so signing up twice updates
    nothing and never creates a duplicate. ``consented_at`` records the explicit
    checkbox rather than assuming consent from the address alone. There is no
    delivery provider in the app yet, so the admin list/CSV is how the list is
    used; ``is_active`` is the unsubscribe switch until a provider supplies one.
    """

    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, default="")
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    consented_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    user_agent: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


Index("ix_subscribers_active_created", Subscriber.is_active, Subscriber.created_at)


class Reservation(Base):
    """A table-booking request from the public site.

    This is a request, not a confirmed booking: the row starts ``pending`` and an
    admin confirms or declines it in the panel. ``date`` and ``time`` are the
    bar-local date and clock the visitor asked for, stored as strings for the
    same reason closures are. There is deliberately no payment or deposit column
    — the policy for those is an owner decision, not code.
    """

    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, default="")  # YYYY-MM-DD
    time: Mapped[str] = mapped_column(String(5), nullable=False, default="")  # HH:MM
    party_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    contact: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # pending | confirmed | declined
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    user_agent: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# The panel asks for "pending first, then nearest date"; the dashboard counts
# pending rows. This index serves both.
Index("ix_reservations_status_date", Reservation.status, Reservation.date)


class Upload(Base):
    """One image uploaded through the admin panel (ticket #50).

    The database stores metadata and filenames, never the bytes: the SQLite file
    has to stay small enough for the backup script. ``filename`` and
    ``thumb_filename`` are generated random names under ``settings.UPLOAD_DIR``,
    both WebP. ``original_name`` is kept only so the owner can recognise the file
    in the panel; it is never used as a path.

    The caption is bilingual like every other piece of content. Alt text is the
    caption for now — a separate field would be the right thing when a public
    gallery lands (#8).
    """

    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    thumb_filename: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False, default="image/webp")
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    caption_en: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    caption_es: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# The admin list is "newest first"; this index keeps it off a full scan.
Index("ix_uploads_created", Upload.created_at)


class Rsvp(Base):
    """One free RSVP for a dated event (ticket #25).

    Deliberately separate from :class:`Reservation`: a reservation asks for a
    table on any night, an RSVP says "I am coming to this event". There is no
    payment or ticket code here — paid ticketing belongs to a provider such as
    Eventbrite, not to a SQLite row. The admin panel sums ``party_size`` to get
    the guest count.
    """

    __tablename__ = "rsvps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("special_events.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    contact: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    party_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ip: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    user_agent: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    event: Mapped["SpecialEvent"] = relationship(back_populates="rsvps")


# The admin list is "newest first" and can be filtered to one event; the guest
# count groups by event. This index serves both.
Index("ix_rsvps_event_created", Rsvp.event_id, Rsvp.created_at)
