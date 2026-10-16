"""Pydantic request/response models.

Read responses always include both languages. The frontend picks the field
matching the visitor's language and falls back to English when a translation is
blank, so a partially-translated schedule still renders.
"""

from datetime import date

from pydantic import BaseModel, Field, field_validator

# One clock decides both what can be created and what gets published, so the
# write guard asks the same `app.ssr` the read filter uses.
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