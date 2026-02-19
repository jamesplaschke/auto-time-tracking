"""Send Slack DM with day classification summary after pull-my-time-for runs."""

from __future__ import annotations

from datetime import date

from .models import BillableType, Confidence, DayClassification


def _fmt_minutes(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def _event_icon(event) -> str:
    if event.billable and event.billable_type == BillableType.REPORTABLE:
        return "💰"
    if event.billable and event.billable_type == BillableType.INVESTMENT:
        return "📊"
    return "📋"


def build_blocks(day: DayClassification) -> list[dict]:
    parsed = date.fromisoformat(day.date)
    day_str = parsed.strftime("%A, %B %-d, %Y")

    tracked = [e for e in day.events if not e.skip]
    skipped = [e for e in day.events if e.skip]
    low_conf = [e for e in tracked if e.confidence == Confidence.LOW]

    billable_minutes = day.total_billable_minutes
    total_minutes = day.total_tracked_minutes

    blocks: list[dict] = []

    # Header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"Time Summary — {day_str}"},
    })

    # Stats
    stats = f"{_fmt_minutes(total_minutes)} tracked  |  {_fmt_minutes(billable_minutes)} billable"
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": stats},
    })

    blocks.append({"type": "divider"})

    # Tracked events
    if tracked:
        lines = []
        for e in tracked:
            icon = _event_icon(e)
            title = e.event.title
            dur = _fmt_minutes(e.duration_minutes)
            if e.project:
                proj = e.project.project_name
                phase = f" › {e.project.phase_name}" if e.project.phase_name else ""
                inv = "  _(investment)_" if e.billable_type == BillableType.INVESTMENT else ""
                lines.append(f"{icon} *{title}*\n   {proj}{phase} · {dur}{inv}")
            else:
                category = e.category or "unclassified"
                lines.append(f"{icon} *{title}*\n   {category} · {dur}")

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n\n".join(lines)},
        })

    # Low confidence warning
    if low_conf:
        warning_lines = [f"⚠️ *{len(low_conf)} event{'s' if len(low_conf) > 1 else ''} need{'s' if len(low_conf) == 1 else ''} review (low confidence):*"]
        for e in low_conf:
            dur = _fmt_minutes(e.duration_minutes)
            warning_lines.append(f"   • {e.event.title} · {dur}")
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(warning_lines)},
        })

    blocks.append({"type": "divider"})

    # Skipped events summary
    context_parts = []
    if skipped:
        skip_titles = [e.event.title for e in skipped[:5]]
        more = len(skipped) - 5
        summary = ", ".join(skip_titles)
        if more > 0:
            summary += f" +{more} more"
        context_parts.append(f"Skipped {len(skipped)} events: {summary}")

    # Footer with instructions
    context_parts.append(
        f"Review `output/{day.date}.json` then run:\n`post-my-time-for {day.date}`"
    )

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "\n\n".join(context_parts)},
    })

    return blocks


def send_day_summary(day: DayClassification, user_id: str, token: str) -> bool:
    """Send a Slack DM with the day summary. Returns True on success."""
    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except ImportError:
        print("Warning: slack-sdk not installed. Run: uv add slack-sdk")
        return False

    client = WebClient(token=token)
    try:
        dm = client.conversations_open(users=[user_id])
        channel_id = dm["channel"]["id"]

        tracked_count = sum(1 for e in day.events if not e.skip)
        fallback = (
            f"Time summary for {day.date}: "
            f"{tracked_count} events tracked, "
            f"{_fmt_minutes(day.total_tracked_minutes)} total, "
            f"{_fmt_minutes(day.total_billable_minutes)} billable"
        )

        blocks = build_blocks(day)
        client.chat_postMessage(channel=channel_id, blocks=blocks, text=fallback)
        return True
    except SlackApiError as e:
        print(f"Warning: Slack notification failed: {e.response['error']}")
        return False
