"""Fetch and normalize events from Google Calendar."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from googleapiclient.discovery import build

from .gcal_auth import get_credentials
from .models import Attendee, CalendarEvent, RSVPStatus

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

# Optional import — only needed when called with a UserConfig
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .users import UserConfig


def _parse_gcal_datetime(dt_dict: dict, default_tz: str = "America/New_York") -> tuple[datetime, bool]:
    """Parse a Google Calendar dateTime or date field.

    Returns (datetime, is_all_day).
    """
    if "date" in dt_dict:
        # All-day event: just a date string like "2026-02-18"
        d = date.fromisoformat(dt_dict["date"])
        return datetime(d.year, d.month, d.day, tzinfo=ZoneInfo(default_tz)), True

    dt_str = dt_dict["dateTime"]
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        tz = dt_dict.get("timeZone", default_tz)
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    return dt, False


def _parse_attendee(att: dict) -> Attendee:
    """Parse a Google Calendar attendee dict."""
    return Attendee(
        email=att.get("email", ""),
        display_name=att.get("displayName"),
        response_status=RSVPStatus(att["responseStatus"]) if "responseStatus" in att else None,
        is_self=att.get("self", False),
        is_organizer=att.get("organizer", False),
    )


def _normalize_event(
    event: dict,
    user_email: str = "jamesp@ketryx.com",
    tz: str = "America/New_York",
) -> CalendarEvent | None:
    """Convert a raw Google Calendar API event to our model.

    Returns None for events that can't be parsed.
    """
    start_raw = event.get("start")
    end_raw = event.get("end")
    if not start_raw or not end_raw:
        return None

    start_dt, is_all_day = _parse_gcal_datetime(start_raw, default_tz=tz)
    end_dt, _ = _parse_gcal_datetime(end_raw, default_tz=tz)

    raw_attendees = event.get("attendees", [])
    attendees = [_parse_attendee(a) for a in raw_attendees]

    # Find self RSVP status
    self_rsvp = None
    for att in attendees:
        if att.is_self or att.email.lower() == user_email.lower():
            self_rsvp = att.response_status
            att.is_self = True
            break

    return CalendarEvent(
        event_id=event.get("id", ""),
        title=event.get("summary", "(No title)"),
        start=start_dt,
        end=end_dt,
        status=event.get("status", "confirmed"),
        all_day=is_all_day,
        attendees=attendees,
        self_rsvp=self_rsvp,
        location=event.get("location"),
        description=event.get("description"),
        recurring_event_id=event.get("recurringEventId"),
    )


def fetch_events(target_date: date, user: UserConfig | None = None) -> list[CalendarEvent]:
    """Fetch all events for a given date from Google Calendar.

    Args:
        target_date: The date to fetch events for.
        user: Optional UserConfig for per-user token path, email, and timezone.
              When None, uses legacy defaults (backward compat).
    """
    from pathlib import Path

    token_path = user.google_token_path if user else None
    user_email = user.email if user else "jamesp@ketryx.com"
    tz_name = user.timezone if user else "America/New_York"

    creds = get_credentials(token_path=token_path)
    service = build("calendar", "v3", credentials=creds)

    tz = ZoneInfo(tz_name)
    start_of_day = datetime(target_date.year, target_date.month, target_date.day, tzinfo=tz)
    end_of_day = start_of_day + timedelta(days=1)

    time_min = start_of_day.isoformat()
    time_max = end_of_day.isoformat()

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    raw_events = events_result.get("items", [])
    events = []
    for raw in raw_events:
        event = _normalize_event(raw, user_email=user_email, tz=tz_name)
        if event is not None:
            events.append(event)

    return events
