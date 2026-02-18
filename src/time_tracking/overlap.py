"""Overlap detection and resolution for classified events."""

from __future__ import annotations

from .models import ClassifiedEvent, Confidence, RSVPStatus


def _priority_score(event: ClassifiedEvent) -> tuple[int, int, int]:
    """Score for tiebreaking overlapping events.

    Higher score wins. Tuple: (rsvp_score, billable_score, duration_score).
    - Accepted > Tentative
    - Client (billable) > Internal (non-billable)
    - Longer > Shorter
    """
    rsvp = event.event.self_rsvp
    rsvp_score = {
        RSVPStatus.ACCEPTED: 3,
        RSVPStatus.NEEDS_ACTION: 2,
        RSVPStatus.TENTATIVE: 1,
        RSVPStatus.DECLINED: 0,
    }.get(rsvp, 2)  # default to needs_action level if None

    billable_score = 1 if event.billable else 0
    duration_score = event.duration_minutes

    return (rsvp_score, billable_score, duration_score)


def _events_overlap(a: ClassifiedEvent, b: ClassifiedEvent) -> bool:
    """Check if two events have overlapping time ranges."""
    return a.event.start < b.event.end and b.event.start < a.event.end


def resolve_overlaps(events: list[ClassifiedEvent]) -> list[ClassifiedEvent]:
    """Resolve overlapping events by keeping the highest-priority one.

    For each overlapping pair, the lower-priority event is marked as skipped.
    Events already marked as skip are ignored.
    """
    # Work on non-skipped events only
    active = [e for e in events if not e.skip]
    skipped = [e for e in events if e.skip]

    # Sort by start time
    active.sort(key=lambda e: e.event.start)

    to_skip: set[str] = set()

    for i in range(len(active)):
        if active[i].event.event_id in to_skip:
            continue
        for j in range(i + 1, len(active)):
            if active[j].event.event_id in to_skip:
                continue
            if not _events_overlap(active[i], active[j]):
                # Since sorted by start, if j doesn't overlap with i,
                # further events might still overlap (different end times)
                if active[j].event.start >= active[i].event.end:
                    break
                continue

            # Overlap detected — skip the lower priority one
            if _priority_score(active[i]) >= _priority_score(active[j]):
                to_skip.add(active[j].event.event_id)
                active[j].skip = True
                active[j].skip_reason = f"overlap with: {active[i].event.title}"
                active[j].duration_minutes = 0
            else:
                to_skip.add(active[i].event.event_id)
                active[i].skip = True
                active[i].skip_reason = f"overlap with: {active[j].event.title}"
                active[i].duration_minutes = 0
                break  # i is now skipped, move on

    return skipped + active
