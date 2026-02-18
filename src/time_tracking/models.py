"""Pydantic data models for calendar events and time entries."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RSVPStatus(str, Enum):
    ACCEPTED = "accepted"
    TENTATIVE = "tentative"
    DECLINED = "declined"
    NEEDS_ACTION = "needsAction"


class BillableType(str, Enum):
    REPORTABLE = "reportable"
    INVESTMENT = "investment"


class Confidence(str, Enum):
    HIGH = "high"
    LOW = "low"


class Attendee(BaseModel):
    email: str
    display_name: Optional[str] = None
    response_status: Optional[RSVPStatus] = None
    is_self: bool = False
    is_organizer: bool = False


class CalendarEvent(BaseModel):
    """Raw event from Google Calendar."""
    event_id: str
    title: str
    start: datetime
    end: datetime
    status: str = "confirmed"  # confirmed, tentative, cancelled
    all_day: bool = False
    attendees: list[Attendee] = Field(default_factory=list)
    self_rsvp: Optional[RSVPStatus] = None
    location: Optional[str] = None
    description: Optional[str] = None
    recurring_event_id: Optional[str] = None


class ProjectMapping(BaseModel):
    """Where to log time in Rocketlane."""
    project_id: int
    project_name: str
    phase_id: Optional[int] = None
    phase_name: Optional[str] = None


class ClassifiedEvent(BaseModel):
    """A calendar event after classification."""
    event: CalendarEvent
    skip: bool = False
    skip_reason: Optional[str] = None
    billable: bool = False
    billable_type: Optional[BillableType] = None
    category: str = ""  # e.g. "client:philips", "overhead:qm-work", "skip:declined"
    project: Optional[ProjectMapping] = None
    confidence: Confidence = Confidence.HIGH
    duration_minutes: int = 0  # after rounding
    notes: str = ""  # what goes into the time entry description
    user_override: Optional[dict] = None  # user can patch classification in JSON
    project_hints: Optional[list[dict]] = None  # suggested projects for unknown-external events


class DayClassification(BaseModel):
    """All classified events for a single day."""
    date: str  # YYYY-MM-DD
    generated_at: str  # ISO timestamp
    events: list[ClassifiedEvent] = Field(default_factory=list)
    total_tracked_minutes: int = 0
    total_billable_minutes: int = 0
    total_non_billable_minutes: int = 0
    skipped_count: int = 0
    low_confidence_count: int = 0


class TimeEntryPayload(BaseModel):
    """Payload for Rocketlane POST /time-entries."""
    date: str  # YYYY-MM-DD
    minutes: int
    notes: str
    billable: bool
    project_id: Optional[int] = None
    phase_id: Optional[int] = None
