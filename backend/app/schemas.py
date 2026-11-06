"""Pydantic request/response models.

Read responses always include both languages. The frontend picks the field
matching the visitor's language and falls back to English when a translation is
blank, so a partially-translated schedule still renders.
"""

import re
import unicodedata
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

# One clock decides both what can be created and what gets published, so the
# write guard asks the same `app.ssr` the read filter uses.
from app.sanitize import clean_text
from app.ssr import bar_today


# --- A weekday: event text plus its hours, saved as one unit ---

class DayScheduleUpdate(BaseModel):
    """Admin write payload for one weekday."""

    title_en: str = Field(default="", max_length=255)
    title_es: str = Field(default="", max_length=255)
    note_en: str = Field(default="", max_length=2000)
    note_es: str = Field(default="", max_length=2000)
    open_time: str = Field(default="", max_length=16)
    close_time: str = Field(default="", max_length=16)
    is_closed: bool = False


class DayScheduleResponse(DayScheduleUpdate):
    """Public read payload for one weekday."""

    day: int = Field(ge=0, le=6)


# --- Closed days ---

class ClosedDayCreate(BaseModel):
    date: date
    reason_en: str = Field(default="", max_length=255)
    reason_es: str = Field(default="", max_length=255)

    @field_validator("date")
    @classmethod
    def _reject_past(cls, v: date) -> date:
        """Closed days must be today or later; past entries are a data-entry mistake.

        Compared against today at the bar rather than on the server, so this
        accepts exactly the dates ``load_closed_days`` will publish. A UTC server
        between 19:00 and midnight would otherwise reject the bar's own today.
        """
        if v < date.fromisoformat(bar_today()[1]):
            raise ValueError("date cannot be in the past")
        return v


class ClosedDayUpdate(BaseModel):
    reason_en: str = Field(default="", max_length=255)
    reason_es: str = Field(default="", max_length=255)


class ClosedDayResponse(BaseModel):
    id: int
    date: str
    reason_en: str
    reason_es: str


# --- Emergency notices ---

NOTICE_SEVERITIES = ("info", "warning", "critical")

# `datetime-local` without seconds: what the admin panel's input emits.
_NOTICE_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")


class NoticeWrite(BaseModel):
    """Admin write payload for one emergency banner.

    At least one language must carry a message: a blank banner would occupy the
    top of the site without telling anyone anything. The window is optional at
    both ends — blank start means "now", blank end means "until switched off".
    """

    message_en: str = Field(default="", max_length=500)
    message_es: str = Field(default="", max_length=500)
    severity: str = Field(default="info", max_length=16)
    starts_at: str = Field(default="", max_length=16)
    ends_at: str = Field(default="", max_length=16)
    is_active: bool = True

    @model_validator(mode="after")
    def _check_values(self):
        if not (self.message_en.strip() or self.message_es.strip()):
            raise ValueError("a notice needs a message in at least one language")

        if self.severity not in NOTICE_SEVERITIES:
            raise ValueError("severity must be info, warning or critical")

        for field in ("starts_at", "ends_at"):
            value = getattr(self, field).strip()
            if not value:
                setattr(self, field, "")
                continue
            if not _NOTICE_TIME_RE.fullmatch(value):
                raise ValueError(f"{field} must be YYYY-MM-DDTHH:MM")
            try:
                datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(f"{field} is not a valid date and time") from exc
            setattr(self, field, value)

        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")

        return self


class NoticeResponse(BaseModel):
    """One notice, with ``is_live`` computed at read time.

    ``is_live`` is the answer to "is this on the site right now?" — active *and*
    inside its window — which is what the admin list needs in order to explain
    why a notice that exists is not showing.
    """

    id: int
    message_en: str
    message_es: str
    severity: str
    starts_at: str
    ends_at: str
    is_active: bool
    is_live: bool = False


# --- Menu ---

def slugify(text: str, fallback: str = "menu") -> str:
    """A URL/anchor-safe slug from a display name: "Cócteles" -> "cocteles".

    Category names are bilingual and typed by hand, so the slug is derived rather
    than trusted: accents are stripped, everything else non-alphanumeric becomes
    a single hyphen. ``fallback`` covers a name that is punctuation only.
    """
    stripped = unicodedata.normalize("NFKD", text or "")
    ascii_only = stripped.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return slug or fallback


# Happy-hour windows are bar-local, so the stored strings are the same shape an
# `<input type="time">` and `<input type="date">` emit.
_PROMO_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_PROMO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_promo_days(value: str) -> str:
    """Canonical weekday list: sorted, deduped, 0 = Sunday; blank means every day.

    Stored as text because SQLite has no array type and the list is at most seven
    two-character entries. Canonicalising here means the read filter can compare
    integers without caring how the panel happened to order the checkboxes.
    """
    days = set()
    for part in (value or "").split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit() or not 0 <= int(part) <= 6:
            raise ValueError("days must be weekday numbers 0-6")
        days.add(int(part))
    return ",".join(str(day) for day in sorted(days))


class MenuPromoBase(BaseModel):
    """One multi-buy offer beneath a drink's headline price.

    The schedule fields are all optional. A blank window means the offer is
    always live; ``is_active`` is the separate off switch.
    """

    label_en: str = Field(default="", max_length=160)
    label_es: str = Field(default="", max_length=160)
    days: str = Field(default="", max_length=20)
    start_time: str = Field(default="", max_length=5)
    end_time: str = Field(default="", max_length=5)
    starts_on: str = Field(default="", max_length=10)
    ends_on: str = Field(default="", max_length=10)
    is_active: bool = True


class MenuPromoWrite(MenuPromoBase):
    """Admin write payload for one promo, including its live window."""

    @model_validator(mode="after")
    def _check_window(self):
        self.days = normalize_promo_days(self.days)

        start = self.start_time.strip()
        end = self.end_time.strip()
        for name, value in (("start_time", start), ("end_time", end)):
            if value and not _PROMO_TIME_RE.fullmatch(value):
                raise ValueError(f"{name} must be HH:MM")
        # Half a window is ambiguous: it could mean "from 6pm" or a forgotten
        # end. Both blank is the explicit "all day" spelling.
        if bool(start) != bool(end):
            raise ValueError("set both start_time and end_time, or neither")
        if start and start == end:
            raise ValueError("start_time and end_time must be different")
        self.start_time, self.end_time = start, end

        for name in ("starts_on", "ends_on"):
            value = getattr(self, name).strip()
            if value:
                if not _PROMO_DATE_RE.fullmatch(value):
                    raise ValueError(f"{name} must be YYYY-MM-DD")
                try:
                    date.fromisoformat(value)
                except ValueError as exc:
                    raise ValueError(f"{name} is not a valid date") from exc
            setattr(self, name, value)

        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on")

        return self


class MenuPromoResponse(MenuPromoBase):
    """One promo as read back, with the schedule resolved against the bar clock."""

    id: int
    sort_order: int
    is_live: bool = True


class MenuCategoryWrite(BaseModel):
    """Admin write payload for one category."""

    name_en: str = Field(default="", max_length=120, validate_default=True)
    name_es: str = Field(default="", max_length=120)
    slug: str = Field(default="", max_length=80)
    is_available: bool = True
    # None means "leave the order alone". A rename must not silently send the
    # section back to the top of the menu; only the reorder buttons set it.
    sort_order: int | None = None

    @field_validator("slug", mode="before")
    @classmethod
    def _derive_slug(cls, v, info):
        """Fill the slug in from the name when the admin leaves it blank.

        Two languages means two candidate names; English leads because it is the
        one that has to be present for the row to render at all.
        """
        if v and str(v).strip():
            return slugify(str(v))
        data = info.data or {}
        name = data.get("name_en") or data.get("name_es") or ""
        return slugify(name)

    @field_validator("name_en")
    @classmethod
    def _require_a_name(cls, v: str) -> str:
        """A category with no English name has no heading to render."""
        if not v.strip():
            raise ValueError("name_en is required")
        return v


class MenuCategoryResponse(MenuCategoryWrite):
    id: int
    sort_order: int
    items: list["MenuItemResponse"] = Field(default_factory=list)

    @field_validator("name_en")
    @classmethod
    def _echo_stored_name(cls, v: str) -> str:
        """A read never rejects stored content.

        A response model stricter than the database would turn one bad row into a
        500 on the public menu, which is a far worse failure than a drink with no
        name on it. Writes stay strict; reads stay honest.
        """
        return v


class MenuItemWrite(BaseModel):
    """Admin write payload for one drink, including its promo list.

    ``promos`` is the complete set rather than a delta: saving an item replaces
    its offers in one transaction, which is what lets the panel add and remove
    promo rows in the same click as the price without a second endpoint.
    """

    category_id: int
    name_en: str = Field(default="", max_length=160, validate_default=True)
    name_es: str = Field(default="", max_length=160)
    description_en: str = Field(default="", max_length=2000)
    description_es: str = Field(default="", max_length=2000)
    ingredients_en: str = Field(default="", max_length=500)
    ingredients_es: str = Field(default="", max_length=500)
    price: str = Field(default="", max_length=32)
    is_available: bool = True
    promos: list[MenuPromoWrite] = Field(default_factory=list)
    # None means "keep the current position", so editing a price cannot reorder
    # the list; the reorder buttons send an explicit value.
    sort_order: int | None = None

    @field_validator("name_en")
    @classmethod
    def _require_a_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name_en is required")
        return v


class MenuItemResponse(MenuItemWrite):
    id: int
    sort_order: int
    promos: list[MenuPromoResponse] = Field(default_factory=list)

    @field_validator("name_en")
    @classmethod
    def _echo_stored_name(cls, v: str) -> str:
        """As above: a read echoes the row rather than second-guessing it."""
        return v


class MenuResponse(BaseModel):
    """The public read: every available category, in order, with its drinks."""

    categories: list[MenuCategoryResponse]


MenuCategoryResponse.model_rebuild()
MenuItemResponse.model_rebuild()


# --- Contact form and the shared inbox ---

CONTACT_NAME_MAX = 120
CONTACT_DETAIL_MAX = 200
CONTACT_SUBJECT_MAX = 160
CONTACT_MESSAGE_MAX = 1000


class ContactWrite(BaseModel):
    """One public contact-form submission.

    ``message`` is capped at 1,000 characters — a number the form also enforces,
    so the limit is visible before a visitor types rather than only after a
    rejected submit. ``website`` is the honeypot: a hidden field real people do
    not fill in. It is accepted rather than rejected so a bot gets the same
    success response as a person.

    The fields are cleaned here, not in the route, so every caller — the public
    endpoint now, an import or a test later — gets the same plain text.
    """

    name: str = Field(default="", max_length=CONTACT_NAME_MAX)
    contact: str = Field(default="", max_length=CONTACT_DETAIL_MAX)
    subject: str = Field(default="", max_length=CONTACT_SUBJECT_MAX)
    message: str = Field(default="", max_length=CONTACT_MESSAGE_MAX)
    website: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def _clean_and_require(self):
        self.name = clean_text(self.name, max_length=CONTACT_NAME_MAX)
        self.contact = clean_text(self.contact, max_length=CONTACT_DETAIL_MAX)
        self.subject = clean_text(self.subject, max_length=CONTACT_SUBJECT_MAX)
        self.message = clean_text(
            self.message, max_length=CONTACT_MESSAGE_MAX, multiline=True
        )
        self.website = (self.website or "").strip()

        if not self.name:
            raise ValueError("name is required")
        if not self.contact:
            raise ValueError("contact is required")
        if not self.message:
            raise ValueError("message is required")
        return self


class ContactResponse(BaseModel):
    """The public endpoint never echoes the submission or its id."""

    ok: bool = True


class SubmissionResponse(BaseModel):
    """One inbox row, exactly as stored — already plain text."""

    id: int
    name: str
    contact: str
    subject: str
    message: str
    ip: str
    user_agent: str
    is_read: bool
    created_at: datetime


class SubmissionListResponse(BaseModel):
    submissions: list[SubmissionResponse]
    unread: int


class SubmissionUpdate(BaseModel):
    """The only editable property of a submission is whether it has been read."""

    is_read: bool


# --- Logs ---
#
# Read-only. There is no write model for either table and no route that accepts
# one, so nothing here can be constructed from a request body — the panel cannot
# edit a log, and neither can anything else.

class LoginAttemptResponse(BaseModel):
    """One login attempt: the username typed, where from, and how it ended.

    There is no password field, on purpose — see ``app.audit.log_login_attempt``.
    """

    id: int
    username: str
    ip: str
    outcome: str
    user_agent: str
    created_at: datetime


class AuditEntryResponse(BaseModel):
    """One change to the menu or the schedule, and who made it."""

    id: int
    area: str
    action: str
    admin_username: str
    ip: str
    user_agent: str
    # "<kind>:<id>" — the panel turns this into a localized label.
    target: str
    target_name: str
    # field -> {"from": ..., "to": ...} for an update; the row's own fields for a
    # create or a delete.
    details: dict = Field(default_factory=dict)
    created_at: datetime


class LoginLogResponse(BaseModel):
    """One page of the login log, newest first."""

    entries: list[LoginAttemptResponse]
    total: int


class AuditLogResponse(BaseModel):
    """One page of the menu or schedule change log, newest first."""

    area: str
    entries: list[AuditEntryResponse]
    total: int