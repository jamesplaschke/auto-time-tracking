"""Send Slack DM with day classification summary after pull-my-time-for runs."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from typing import TYPE_CHECKING

from .models import BillableType, Confidence, DayClassification

if TYPE_CHECKING:
    from .users import UserConfig

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache"
_PENDING_FILE = CACHE_DIR / "pending_messages.json"


def _load_pending() -> dict:
    if _PENDING_FILE.exists():
        return json.loads(_PENDING_FILE.read_text())
    return {}


def _save_pending(data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _PENDING_FILE.write_text(json.dumps(data, indent=2))


def _fmt_minutes(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"



def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


def _billable_label(event) -> str:
    if not event.billable:
        return "non-billable"
    if event.billable_type == BillableType.INVESTMENT:
        return "investment"
    return "reportable"


def _build_table(day: DayClassification) -> str:
    """Build a fixed-width ASCII table for the tracked events."""
    tracked = [e for e in day.events if not e.skip]

    # Column widths
    W_TITLE = 26
    W_PROJECT = 22
    W_TYPE = 13   # "non-billable" is 12 chars
    W_DUR = 6

    header = (
        f"{'Event':<{W_TITLE}}  {'Project':<{W_PROJECT}}  {'Type':<{W_TYPE}}  {'Time':>{W_DUR}}"
    )
    sep = "-" * len(header)

    rows = [header, sep]
    for e in tracked:
        title = _truncate(e.event.title, W_TITLE)
        if e.project:
            proj = _truncate(e.project.project_name, W_PROJECT)
        else:
            proj = _truncate(e.category or "unclassified", W_PROJECT)
        label = _billable_label(e)
        dur = _fmt_minutes(e.duration_minutes)
        rows.append(
            f"{title:<{W_TITLE}}  {proj:<{W_PROJECT}}  {label:<{W_TYPE}}  {dur:>{W_DUR}}"
        )

    rows.append(sep)
    total_dur = _fmt_minutes(day.total_tracked_minutes)
    billable_dur = _fmt_minutes(day.total_billable_minutes)
    summary = f"{'Total: ' + total_dur:<{W_TITLE + W_PROJECT + W_TYPE + 4}}  {'Bill: ' + billable_dur:>{W_DUR}}"
    rows.append(summary)

    return "\n".join(rows)


def build_blocks(day: DayClassification) -> list[dict]:
    parsed = date.fromisoformat(day.date)
    day_str = parsed.strftime("%A, %B %-d, %Y")

    tracked = [e for e in day.events if not e.skip]
    skipped = [e for e in day.events if e.skip]
    low_conf = [e for e in tracked if e.confidence == Confidence.LOW]

    blocks: list[dict] = []

    # Header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"Time Summary — {day_str}"},
    })

    blocks.append({"type": "divider"})

    # Table in a code block so monospace alignment renders correctly
    if tracked:
        table = _build_table(day)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```{table}```"},
        })

    # Low confidence warning
    if low_conf:
        n = len(low_conf)
        warning = f"⚠️ *{n} event{'s' if n > 1 else ''} need review (low confidence):*\n"
        warning += "\n".join(f"  • {e.event.title} · {_fmt_minutes(e.duration_minutes)}" for e in low_conf)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": warning},
        })

    blocks.append({"type": "divider"})

    # Skipped + footer
    footer_parts = []
    if skipped:
        skip_titles = [e.event.title for e in skipped[:5]]
        more = len(skipped) - 5
        summary = ", ".join(skip_titles)
        if more > 0:
            summary += f" +{more} more"
        footer_parts.append(f"Skipped {len(skipped)} events: {summary}")

    footer_parts.append(
        f"Reply in this thread to correct classifications, or click the button to post."
    )

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "\n\n".join(footer_parts)},
    })

    # "Post to Rocketlane" button
    blocks.append({
        "type": "actions",
        "elements": [{
            "type": "button",
            "text": {"type": "plain_text", "text": "Post to Rocketlane"},
            "style": "primary",
            "action_id": "post_to_rocketlane",
            "value": day.date,
        }],
    })

    return blocks


def send_day_summary(
    day: DayClassification,
    user_id: str,
    token: str,
    user: UserConfig | None = None,
) -> bool:
    """Send a Slack DM with the day summary. Returns True on success.

    Args:
        day: The classified day to summarize.
        user_id: Slack user ID to DM.
        token: Slack bot token.
        user: Optional UserConfig — when provided, stores user_config_id
              in the pending cache so the listener can resolve the correct user.
    """
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
        resp = client.chat_postMessage(channel=channel_id, blocks=blocks, text=fallback)

        # Write to pending cache so the listener knows which date this thread belongs to
        message_ts = resp["ts"]
        pending = _load_pending()
        entry = {
            "date": day.date,
            "channel_id": channel_id,
            "user_id": user_id,
        }
        if user:
            entry["user_config_id"] = user.user_id
        pending[message_ts] = entry
        _save_pending(pending)

        return True
    except SlackApiError as e:
        print(f"Warning: Slack notification failed: {e.response['error']}")
        return False
