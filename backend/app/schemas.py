"""Pydantic request/response models."""

from datetime import date

from pydantic import BaseModel, Field, field_validator


# --- Auth ---

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=255)


# --- Events ---

class EventUpdate(BaseModel):
    title: str = Field(default="", max_length=255)
    note: str = Field(default="", max_length=2000)
    time: str = Field(default="", max_length=64)


class EventResponse(BaseModel):
    day: int = Field(ge=0, le=6)
    title: str
    note: str
    time: str


# --- Hours ---

class HoursUpdate(BaseModel):
    open_time: str = Field(default="", max_length=16)
    close_time: str = Field(default="", max_length=16)
    is_closed: bool = False


class HoursResponse(BaseModel):
    day: int = Field(ge=0, le=6)
    open_time: str
    close_time: str
    is_closed: bool


# --- Closed Days ---

class ClosedDayCreate(BaseModel):
    date: date
    reason: str = Field(default="", max_length=255)

    @field_validator("date")
    @classmethod
    def _reject_past(cls, v: date) -> date:
        """Closed days must be today or later; past entries are a data-entry mistake."""
        if v < date.today():
            raise ValueError("date cannot be in the past")
        return v


class ClosedDayResponse(BaseModel):
    id: int
    date: str
    reason: str
