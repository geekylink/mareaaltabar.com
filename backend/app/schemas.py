"""Pydantic request/response models.

Read responses always include both languages. The frontend picks the field
matching the visitor's language and falls back to English when a translation is
blank, so a partially-translated schedule still renders.
"""

import re
import unicodedata
from datetime import date, datetime, timedelta

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


# --- Dated / special events ---

EVENT_TITLE_MAX = 255
EVENT_DESCRIPTION_MAX = 2000
EVENT_IMAGE_MAX = 500


class SpecialEventBase(BaseModel):
    """The editable half of a dated event, shared by write and read.

    Times are optional and must arrive as a pair; an end before the start is an
    overnight event, exactly as a happy-hour promo can be. ``image_url`` is a
    link, not an upload (#50 owns uploads), and is restricted to http(s) or a
    site-relative path so an admin cannot paste a ``javascript:`` URL into an
    ``<img src>``.
    """

    title_en: str = Field(default="", max_length=EVENT_TITLE_MAX)
    title_es: str = Field(default="", max_length=EVENT_TITLE_MAX)
    description_en: str = Field(default="", max_length=EVENT_DESCRIPTION_MAX)
    description_es: str = Field(default="", max_length=EVENT_DESCRIPTION_MAX)
    start_time: str = Field(default="", max_length=5)
    end_time: str = Field(default="", max_length=5)
    image_url: str = Field(default="", max_length=EVENT_IMAGE_MAX)
    is_active: bool = True

    @model_validator(mode="after")
    def _clean(self):
        for name in ("title_en", "title_es", "description_en", "description_es"):
            setattr(self, name, getattr(self, name).strip())

        start = self.start_time.strip()
        end = self.end_time.strip()
        for name, value in (("start_time", start), ("end_time", end)):
            if value and not _HHMM_RE.fullmatch(value):
                raise ValueError(f"{name} must be HH:MM")
        if bool(start) != bool(end):
            raise ValueError("set both start_time and end_time, or neither")
        if start and start == end:
            raise ValueError("start_time and end_time must be different")
        self.start_time, self.end_time = start, end

        image = self.image_url.strip()
        if image and not (
            image.startswith("https://")
            or image.startswith("http://")
            or image.startswith("/")
        ):
            raise ValueError("image_url must be an http(s) or site-relative URL")
        self.image_url = image

        if not self.title_en and not self.title_es:
            raise ValueError("a title is required in at least one language")
        return self


class SpecialEventCreate(SpecialEventBase):
    date: date

    @field_validator("date")
    @classmethod
    def _reject_past(cls, v: date) -> date:
        """A new event is for today or later, at the bar's clock.

        Edits are exempt (:class:`SpecialEventUpdate`): an admin must be able to
        fix the wording on an event that has already happened without first
        moving its date into the future.
        """
        if v < date.fromisoformat(bar_today()[1]):
            raise ValueError("date cannot be in the past")
        return v


class SpecialEventUpdate(SpecialEventBase):
    date: date


class SpecialEventResponse(SpecialEventBase):
    """One event as read back, with its date and whether it has passed."""

    id: int
    date: str
    is_past: bool = False


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


# Windows and dates are bar-local, so the stored strings are the same shape an
# `<input type="time">` and `<input type="date">` emit.
_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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
            if value and not _HHMM_RE.fullmatch(value):
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
                if not _ISO_DATE_RE.fullmatch(value):
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
    # At most one drink carries this at a time. The menu write handlers clear it
    # on every other row when a save sets it, so the hero has one answer.
    is_drink_of_day: bool = False
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


# --- Generic content tables (ticket #17) ----------------------------------
#
# One section (a heading and its shared copy) with any number of items beneath
# it. The same rows back the About box, the package lists and the gallery, so the
# write models are deliberately generic: a title, body, optional price, optional
# image URL and an optional date window. The public read filters on the window;
# the admin read keeps everything so an expired item can be edited and reused.

CONTENT_TITLE_MAX = 255
CONTENT_BODY_MAX = 4000
CONTENT_PRICE_MAX = 32
CONTENT_IMAGE_MAX = 500


def _check_optional_url(value: str, field: str) -> str:
    """Trim a URL and reject anything that could not go into ``src``/``href``."""
    url = (value or "").strip()
    if url and not (
        url.startswith("https://")
        or url.startswith("http://")
        or url.startswith("/")
    ):
        raise ValueError(f"{field} must be an http(s) or site-relative URL")
    return url


def _check_optional_date(value: str, field: str) -> str:
    """Normalise an optional ISO date, rejecting impossible ones."""
    text = (value or "").strip()
    if text:
        if not _ISO_DATE_RE.fullmatch(text):
            raise ValueError(f"{field} must be YYYY-MM-DD")
        try:
            date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"{field} is not a valid date") from exc
    return text


class ContentSectionWrite(BaseModel):
    """Admin write payload for one content section.

    A blank slug is derived from the English title (or Spanish when English is
    blank), exactly as a menu category's slug is, so publishing never requires
    the owner to understand what a slug is.
    """

    slug: str = Field(default="", max_length=80)
    title_en: str = Field(default="", max_length=CONTENT_TITLE_MAX)
    title_es: str = Field(default="", max_length=CONTENT_TITLE_MAX)
    body_en: str = Field(default="", max_length=CONTENT_BODY_MAX)
    body_es: str = Field(default="", max_length=CONTENT_BODY_MAX)
    is_active: bool = True
    sort_order: int | None = None

    @model_validator(mode="after")
    def _clean_and_derive(self):
        for name in ("title_en", "title_es", "body_en", "body_es"):
            setattr(self, name, getattr(self, name).strip())

        if not (self.title_en or self.title_es):
            raise ValueError("a title is required in at least one language")

        self.slug = (self.slug or "").strip()
        if not self.slug:
            self.slug = slugify(self.title_en or self.title_es, fallback="section")
        else:
            self.slug = slugify(self.slug, fallback="section")
        return self


class ContentSectionResponse(BaseModel):
    id: int
    slug: str
    title_en: str
    title_es: str
    body_en: str
    body_es: str
    sort_order: int
    is_active: bool
    items: list["ContentItemResponse"] = Field(default_factory=list)


class ContentItemWrite(BaseModel):
    """Admin write payload for one row inside a section.

    ``section_id`` is on the item rather than the URL because moving an item
    between sections is an ordinary edit, not a delete and re-create.
    """

    section_id: int
    title_en: str = Field(default="", max_length=CONTENT_TITLE_MAX)
    title_es: str = Field(default="", max_length=CONTENT_TITLE_MAX)
    body_en: str = Field(default="", max_length=CONTENT_BODY_MAX)
    body_es: str = Field(default="", max_length=CONTENT_BODY_MAX)
    price: str = Field(default="", max_length=CONTENT_PRICE_MAX)
    image_url: str = Field(default="", max_length=CONTENT_IMAGE_MAX)
    starts_on: str = Field(default="", max_length=10)
    ends_on: str = Field(default="", max_length=10)
    is_active: bool = True
    sort_order: int | None = None

    @model_validator(mode="after")
    def _clean_and_check(self):
        for name in ("title_en", "title_es", "body_en", "body_es"):
            setattr(self, name, getattr(self, name).strip())
        if not (self.title_en or self.title_es):
            raise ValueError("a title is required in at least one language")

        self.price = (self.price or "").strip()
        self.image_url = _check_optional_url(self.image_url, "image_url")
        self.starts_on = _check_optional_date(self.starts_on, "starts_on")
        self.ends_on = _check_optional_date(self.ends_on, "ends_on")
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on")
        return self


class ContentItemResponse(BaseModel):
    id: int
    section_id: int
    title_en: str
    title_es: str
    body_en: str
    body_es: str
    price: str
    image_url: str
    starts_on: str
    ends_on: str
    sort_order: int
    is_active: bool
    # Public reads only return rows that are live; the admin read uses this to
    # explain why an active-looking row is not on the site.
    is_live: bool = True


ContentSectionResponse.model_rebuild()


# --- News / blog (ticket #24) ---------------------------------------------
#
# A post is a dated article with its own slug, excerpt and optional image. The
# public read hides drafts and anything dated after today at the bar; the admin
# read keeps every row so a scheduled post can be written and checked first.

BLOG_TITLE_MAX = 255
BLOG_EXCERPT_MAX = 500
BLOG_BODY_MAX = 20000
BLOG_SLUG_MAX = 120
BLOG_IMAGE_MAX = 500


class BlogPostWrite(BaseModel):
    """Admin write payload for one news post.

    A blank slug is derived from the English title (or Spanish when English is
    blank), and a blank publication date defaults to today at the bar. Both are
    conveniences for the owner, not hidden rules: the panel shows the resolved
    values after saving.
    """

    slug: str = Field(default="", max_length=BLOG_SLUG_MAX)
    title_en: str = Field(default="", max_length=BLOG_TITLE_MAX)
    title_es: str = Field(default="", max_length=BLOG_TITLE_MAX)
    excerpt_en: str = Field(default="", max_length=BLOG_EXCERPT_MAX)
    excerpt_es: str = Field(default="", max_length=BLOG_EXCERPT_MAX)
    body_en: str = Field(default="", max_length=BLOG_BODY_MAX)
    body_es: str = Field(default="", max_length=BLOG_BODY_MAX)
    image_url: str = Field(default="", max_length=BLOG_IMAGE_MAX)
    published_on: str = Field(default="", max_length=10)
    is_active: bool = True

    @model_validator(mode="after")
    def _clean_and_derive(self):
        for name in ("title_en", "title_es", "excerpt_en", "excerpt_es", "body_en", "body_es"):
            setattr(self, name, (getattr(self, name) or "").strip())

        if not (self.title_en or self.title_es):
            raise ValueError("a title is required in at least one language")

        self.slug = (self.slug or "").strip()
        if not self.slug:
            self.slug = slugify(self.title_en or self.title_es, fallback="post")
        else:
            self.slug = slugify(self.slug, fallback="post")

        self.image_url = _check_optional_url(self.image_url, "image_url")
        self.published_on = _check_optional_date(self.published_on, "published_on") or bar_today()[1]
        return self


class BlogPostResponse(BaseModel):
    id: int
    slug: str
    title_en: str
    title_es: str
    excerpt_en: str
    excerpt_es: str
    body_en: str
    body_es: str
    image_url: str
    published_on: str
    is_active: bool
    # Public reads only return live posts; the admin read uses this to explain
    # why a row is not on the site yet.
    is_live: bool = True


# --- Newsletter (ticket #12) ----------------------------------------------

NEWSLETTER_NAME_MAX = 120
NEWSLETTER_EMAIL_MAX = 254

# Deliberately loose: the address is stored for a human to use, not verified by
# an SMTP round trip (there is no provider yet). This catches typos and refusal
# without pretending to be RFC 5322.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class NewsletterWrite(BaseModel):
    """One public newsletter signup.

    ``consent`` is required rather than inferred. A checkbox that must be ticked
    is the explicit signal a privacy policy can point at; an address typed into
    an email field is not. ``website`` is the same honeypot the contact form uses.
    """

    email: str = Field(default="", max_length=NEWSLETTER_EMAIL_MAX)
    name: str = Field(default="", max_length=NEWSLETTER_NAME_MAX)
    consent: bool = False
    website: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def _clean_and_require(self):
        self.email = clean_text(self.email, max_length=NEWSLETTER_EMAIL_MAX).lower()
        self.name = clean_text(self.name, max_length=NEWSLETTER_NAME_MAX)
        self.website = (self.website or "").strip()

        if not self.consent:
            raise ValueError("consent is required")
        if not self.email:
            raise ValueError("email is required")
        if not _EMAIL_RE.fullmatch(self.email):
            raise ValueError("email is not a valid address")
        return self


class NewsletterResponse(BaseModel):
    """The public endpoint never reveals whether an address was already stored."""

    ok: bool = True


class SubscriberResponse(BaseModel):
    id: int
    email: str
    name: str
    consented_at: datetime | None
    ip: str
    user_agent: str
    is_active: bool
    created_at: datetime


class SubscriberListResponse(BaseModel):
    subscribers: list[SubscriberResponse]
    total: int
    active: int


class SubscriberUpdate(BaseModel):
    is_active: bool


# --- Reservation requests (ticket #14) ------------------------------------

RESERVATION_MAX_GUESTS = 20
RESERVATION_MAX_DAYS_AHEAD = 90
RESERVATION_STATUSES = ("pending", "confirmed", "declined")


class ReservationWrite(BaseModel):
    """A table-booking request from the public site.

    This is a request, not a confirmation. The date must be today or later at
    the bar and no more than 90 days out, the time must be a real ``HH:MM``, and
    the party size is capped so the form cannot be used to book out the whole
    bar without a conversation.
    """

    date: date
    time: str = Field(default="", max_length=5)
    party_size: int = Field(default=2, ge=1, le=RESERVATION_MAX_GUESTS)
    name: str = Field(default="", max_length=CONTACT_NAME_MAX)
    contact: str = Field(default="", max_length=CONTACT_DETAIL_MAX)
    notes: str = Field(default="", max_length=CONTACT_MESSAGE_MAX)
    website: str = Field(default="", max_length=200)

    @field_validator("date")
    @classmethod
    def _check_date(cls, v: date) -> date:
        today = date.fromisoformat(bar_today()[1])
        if v < today:
            raise ValueError("date cannot be in the past")
        if v > today + timedelta(days=RESERVATION_MAX_DAYS_AHEAD):
            raise ValueError(
                f"date cannot be more than {RESERVATION_MAX_DAYS_AHEAD} days ahead"
            )
        return v

    @model_validator(mode="after")
    def _clean_and_require(self):
        self.time = (self.time or "").strip()
        if not _HHMM_RE.fullmatch(self.time):
            raise ValueError("time must be HH:MM")
        self.name = clean_text(self.name, max_length=CONTACT_NAME_MAX)
        self.contact = clean_text(self.contact, max_length=CONTACT_DETAIL_MAX)
        self.notes = clean_text(
            self.notes, max_length=CONTACT_MESSAGE_MAX, multiline=True
        )
        self.website = (self.website or "").strip()

        if not self.name:
            raise ValueError("name is required")
        if not self.contact:
            raise ValueError("contact is required")
        return self


class ReservationCreated(BaseModel):
    """The public endpoint acknowledges a request without exposing the row."""

    ok: bool = True


class ReservationResponse(BaseModel):
    id: int
    date: str
    time: str
    party_size: int
    name: str
    contact: str
    notes: str
    status: str
    ip: str
    user_agent: str
    created_at: datetime
    updated_at: datetime


class ReservationListResponse(BaseModel):
    reservations: list[ReservationResponse]
    pending: int


class ReservationUpdate(BaseModel):
    """The only editable property of a request is its outcome."""

    status: str = Field(default="pending", max_length=16)

    @field_validator("status")
    @classmethod
    def _known_status(cls, v: str) -> str:
        if v not in RESERVATION_STATUSES:
            raise ValueError("status must be pending, confirmed or declined")
        return v


# --- Event RSVPs (ticket #25) ---------------------------------------------


class RsvpWrite(BaseModel):
    """A free RSVP for one dated event.

    The event id is in the URL, not the body, so the write cannot accidentally
    attach a guest to a different event. The same honeypot and contact limits as
    the other public forms apply; ``party_size`` is capped so one RSVP cannot
    claim the whole event.
    """

    name: str = Field(default="", max_length=CONTACT_NAME_MAX)
    contact: str = Field(default="", max_length=CONTACT_DETAIL_MAX)
    party_size: int = Field(default=2, ge=1, le=RESERVATION_MAX_GUESTS)
    notes: str = Field(default="", max_length=CONTACT_MESSAGE_MAX)
    website: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def _clean_and_require(self):
        self.name = clean_text(self.name, max_length=CONTACT_NAME_MAX)
        self.contact = clean_text(self.contact, max_length=CONTACT_DETAIL_MAX)
        self.notes = clean_text(
            self.notes, max_length=CONTACT_MESSAGE_MAX, multiline=True
        )
        self.website = (self.website or "").strip()

        if not self.name:
            raise ValueError("name is required")
        if not self.contact:
            raise ValueError("contact is required")
        return self


class RsvpCreated(BaseModel):
    """The public endpoint acknowledges an RSVP without exposing the row."""

    ok: bool = True


class RsvpResponse(BaseModel):
    """One RSVP as the admin panel reads it, with its event's identity."""

    id: int
    event_id: int
    event_date: str
    event_title_en: str
    event_title_es: str
    name: str
    contact: str
    party_size: int
    notes: str
    ip: str
    user_agent: str
    created_at: datetime


class RsvpListResponse(BaseModel):
    rsvps: list[RsvpResponse]
    total_rsvps: int
    total_guests: int


# --- Uploaded images (ticket #50) -----------------------------------------

UPLOAD_CAPTION_MAX = 500


class UploadResponse(BaseModel):
    """One stored image, with the URLs the panel and a future gallery need."""

    id: int
    filename: str
    thumb_filename: str
    url: str
    thumb_url: str
    original_name: str
    mime_type: str
    width: int
    height: int
    size_bytes: int
    caption_en: str
    caption_es: str
    created_at: datetime


class UploadUpdate(BaseModel):
    """The only editable part of an upload: its bilingual caption."""

    caption_en: str = Field(default="", max_length=UPLOAD_CAPTION_MAX)
    caption_es: str = Field(default="", max_length=UPLOAD_CAPTION_MAX)

    @model_validator(mode="after")
    def _clean(self):
        self.caption_en = clean_text(self.caption_en, max_length=UPLOAD_CAPTION_MAX)
        self.caption_es = clean_text(self.caption_es, max_length=UPLOAD_CAPTION_MAX)
        return self


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