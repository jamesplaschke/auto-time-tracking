"""Rule-based classification engine for calendar events."""

from __future__ import annotations

import math

from .config import (
    ENTERPRISE_POD_DEFAULT_PHASE_NAME,
    ENTERPRISE_POD_PATTERN,
    ENTERPRISE_POD_PROJECT_ID,
    ENTERPRISE_POD_PROJECT_NAME,
    IGNORED_DOMAINS,
    KETRYX_DOMAIN,
    MIN_DURATION_MINUTES,
    OVERHEAD_PHASES,
    OVERHEAD_PROJECT_ID,
    OVERHEAD_PROJECT_NAME,
    ROUNDING_INCREMENT_MINUTES,
    SKIP_TITLE_PATTERNS,
    SUPPORT_TICKETS_NAME,
    SUPPORT_TICKETS_PROJECT_ID,
    VALUE_ENGINEERING_PATTERN,
    find_client_by_domain,
    find_client_by_title,
    get_domain,
    is_investment_title,
    is_support_ticket,
    match_client_phase,
    match_overhead_phase,
    resolve_project,
)
from .models import (
    BillableType,
    CalendarEvent,
    ClassifiedEvent,
    Confidence,
    ProjectMapping,
    RSVPStatus,
)


def round_duration(minutes: float) -> int:
    """Round to nearest ROUNDING_INCREMENT, minimum MIN_DURATION."""
    if minutes <= 0:
        return 0
    rounded = max(
        MIN_DURATION_MINUTES,
        int(math.ceil(minutes / ROUNDING_INCREMENT_MINUTES) * ROUNDING_INCREMENT_MINUTES),
    )
    return rounded


def _calc_duration_minutes(event: CalendarEvent) -> float:
    """Calculate raw duration in minutes."""
    delta = event.end - event.start
    return delta.total_seconds() / 60


def _should_skip(event: CalendarEvent) -> str | None:
    """Check if event should be skipped entirely. Returns reason or None."""
    # Cancelled
    if event.status == "cancelled":
        return "cancelled"

    # Declined
    if event.self_rsvp == RSVPStatus.DECLINED:
        return "declined"

    # All-day events
    if event.all_day:
        return "all-day event"

    # Title-based skip patterns
    for pattern in SKIP_TITLE_PATTERNS:
        if pattern.search(event.title):
            return f"title match: {pattern.pattern}"

    # Zero or negative duration
    if _calc_duration_minutes(event) <= 0:
        return "zero duration"

    return None


def _extract_domains(event: CalendarEvent) -> tuple[set[str], set[str]]:
    """Partition attendee domains into client (external) and internal.

    Returns (client_domains, internal_domains).
    Self is excluded from both sets.
    """
    client_domains: set[str] = set()
    internal_domains: set[str] = set()

    for att in event.attendees:
        if att.is_self:
            continue
        domain = get_domain(att.email)
        if not domain or domain in IGNORED_DOMAINS:
            continue
        if domain == KETRYX_DOMAIN:
            internal_domains.add(domain)
        else:
            client_domains.add(domain)

    return client_domains, internal_domains


def classify_event(event: CalendarEvent) -> ClassifiedEvent:
    """Classify a single calendar event using the decision tree."""
    raw_minutes = _calc_duration_minutes(event)
    duration = round_duration(raw_minutes)

    # Step 1: Skip check
    skip_reason = _should_skip(event)
    if skip_reason:
        return ClassifiedEvent(
            event=event,
            skip=True,
            skip_reason=skip_reason,
            category=f"skip:{skip_reason.split(':')[0].strip()}",
            duration_minutes=0,
            notes=event.title,
        )

    # Step 2: Check for support ticket pattern (title-based, before domain check)
    if is_support_ticket(event.title):
        return ClassifiedEvent(
            event=event,
            billable=True,
            billable_type=BillableType.INVESTMENT,
            category="support-tickets",
            project=ProjectMapping(
                project_id=SUPPORT_TICKETS_PROJECT_ID,
                project_name=SUPPORT_TICKETS_NAME,
            ),
            confidence=Confidence.HIGH,
            duration_minutes=duration,
            notes=event.title,
        )

    # Step 2.5: Check for Enterprise Account Pods (title-based)
    # Covers: Enterprise Methodology Pod, Hockey Stick, POD 1, Commercial Pod 1
    if ENTERPRISE_POD_PATTERN.search(event.title):
        return ClassifiedEvent(
            event=event,
            billable=True,
            billable_type=BillableType.INVESTMENT,
            category="enterprise-pod",
            project=ProjectMapping(
                project_id=ENTERPRISE_POD_PROJECT_ID,
                project_name=ENTERPRISE_POD_PROJECT_NAME,
                phase_name=ENTERPRISE_POD_DEFAULT_PHASE_NAME,
            ),
            confidence=Confidence.HIGH,
            duration_minutes=duration,
            notes=event.title,
        )

    # Step 3: Check for value engineering (title-based, maps to Overhead > Enabling Work)
    if VALUE_ENGINEERING_PATTERN.search(event.title):
        enabling_phase = next(
            (p for p in OVERHEAD_PHASES if p.name == "Enabling Work"),
            OVERHEAD_PHASES[-1],
        )
        return ClassifiedEvent(
            event=event,
            billable=False,
            category="overhead:enabling-work",
            project=ProjectMapping(
                project_id=OVERHEAD_PROJECT_ID,
                project_name=OVERHEAD_PROJECT_NAME,
                phase_id=enabling_phase.phase_id,
                phase_name=enabling_phase.name,
            ),
            confidence=Confidence.HIGH,
            duration_minutes=duration,
            notes=f"Value engineering: {event.title}",
        )

    # Step 4: Extract domains from attendees
    client_domains, internal_domains = _extract_domains(event)

    # Step 5: Client match — if we find a known client domain
    if client_domains:
        for domain in client_domains:
            client = find_client_by_domain(domain)
            if client:
                project_id, project_name = resolve_project(client, event.title)
                billable_type = (
                    BillableType.INVESTMENT
                    if is_investment_title(event.title)
                    else BillableType.REPORTABLE
                )
                phase_name = match_client_phase(client, event.title)
                return ClassifiedEvent(
                    event=event,
                    billable=True,
                    billable_type=billable_type,
                    category=f"client:{project_name.lower().replace(' ', '-')}",
                    project=ProjectMapping(
                        project_id=project_id,
                        project_name=project_name,
                        phase_name=phase_name,
                    ),
                    confidence=Confidence.HIGH,
                    duration_minutes=duration,
                    notes=event.title,
                )

        # Unknown external domain — flag as low confidence
        unknown_domains = ", ".join(sorted(client_domains))
        return ClassifiedEvent(
            event=event,
            billable=False,
            category=f"unknown-external:{unknown_domains}",
            confidence=Confidence.LOW,
            duration_minutes=duration,
            notes=event.title,
        )

    # Step 5.5: Title-pattern client match — catches solo work and internal meetings
    # whose title references a client (e.g. "philips config", "Philips Daily Internal Sync")
    client = find_client_by_title(event.title)
    if client:
        project_id, project_name = resolve_project(client, event.title)
        billable_type = (
            BillableType.INVESTMENT
            if is_investment_title(event.title)
            else BillableType.REPORTABLE
        )
        phase_name = match_client_phase(client, event.title)
        return ClassifiedEvent(
            event=event,
            billable=True,
            billable_type=billable_type,
            category=f"client:{project_name.lower().replace(' ', '-')}",
            project=ProjectMapping(
                project_id=project_id,
                project_name=project_name,
                phase_name=phase_name,
            ),
            confidence=Confidence.HIGH,
            duration_minutes=duration,
            notes=event.title,
        )

    # Step 6: Internal-only event — match to overhead phase by title
    if internal_domains or event.attendees:
        phase = match_overhead_phase(event.title)
        return ClassifiedEvent(
            event=event,
            billable=False,
            category=f"overhead:{phase.name.lower().replace(' ', '-')}",
            project=ProjectMapping(
                project_id=OVERHEAD_PROJECT_ID,
                project_name=OVERHEAD_PROJECT_NAME,
                phase_id=phase.phase_id,
                phase_name=phase.name,
            ),
            confidence=Confidence.HIGH,
            duration_minutes=duration,
            notes=event.title,
        )

    # Step 7: No attendees — try title match for overhead, otherwise low confidence
    phase = match_overhead_phase(event.title)
    if phase.title_patterns:  # matched a specific phase (not the catch-all)
        return ClassifiedEvent(
            event=event,
            billable=False,
            category=f"overhead:{phase.name.lower().replace(' ', '-')}",
            project=ProjectMapping(
                project_id=OVERHEAD_PROJECT_ID,
                project_name=OVERHEAD_PROJECT_NAME,
                phase_id=phase.phase_id,
                phase_name=phase.name,
            ),
            confidence=Confidence.HIGH,
            duration_minutes=duration,
            notes=event.title,
        )

    # Fallback: no attendees, no pattern match → low confidence
    return ClassifiedEvent(
        event=event,
        billable=False,
        category="unknown:no-match",
        confidence=Confidence.LOW,
        duration_minutes=duration,
        notes=event.title,
    )


def classify_events(events: list[CalendarEvent]) -> list[ClassifiedEvent]:
    """Classify a list of calendar events."""
    return [classify_event(e) for e in events]
