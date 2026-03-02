"""Slack Socket Mode daemon — handles button clicks and thread replies for time tracking.

Start with: uv run time-tracking-listener
Requires SLACK_APP_TOKEN (xapp-...) and SLACK_BOT_TOKEN in .env
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from threading import Event

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = BASE_DIR / "cache"
_PENDING_FILE = CACHE_DIR / "pending_messages.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_pending() -> dict:
    if _PENDING_FILE.exists():
        return json.loads(_PENDING_FILE.read_text())
    return {}


def _resolve_user(pending_entry: dict):
    """Resolve a UserConfig from a pending cache entry. Returns None for legacy entries."""
    user_config_id = pending_entry.get("user_config_id")
    if not user_config_id:
        return None
    try:
        from .users import get_user
        return get_user(user_config_id)
    except KeyError:
        return None


def _output_dir_for_user(user) -> Path:
    """Get the output directory for a user, falling back to legacy path."""
    if user:
        return user.output_dir
    return BASE_DIR / "output"


def _load_day(date_str: str, user=None):
    from .models import DayClassification
    output_dir = _output_dir_for_user(user)
    path = output_dir / f"{date_str}.json"
    if not path.exists():
        raise FileNotFoundError(f"No classified file for {date_str}. Run pull-my-time-for first.")
    return DayClassification.model_validate(json.loads(path.read_text()))


def _save_day(day, user=None) -> None:
    output_dir = _output_dir_for_user(user)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{day.date}.json"
    path.write_text(day.model_dump_json(indent=2))


def _update_message(web_client, channel_id: str, ts: str, text: str, blocks: list | None = None) -> None:
    kwargs = {"channel": channel_id, "ts": ts, "text": text}
    if blocks is not None:
        kwargs["blocks"] = blocks
    web_client.chat_update(**kwargs)


# ---------------------------------------------------------------------------
# Button handler — "Post to Rocketlane"
# ---------------------------------------------------------------------------

def handle_button(web_client, payload: dict) -> None:
    action = payload["actions"][0]
    date_str = action["value"]
    channel_id = payload["channel"]["id"]
    message_ts = payload["message"]["ts"]

    # Resolve user from pending cache
    pending = _load_pending()
    pending_entry = pending.get(message_ts, {})
    user = _resolve_user(pending_entry)
    api_key = user.rocketlane_api_key if user else None

    # Immediately show spinner
    _update_message(
        web_client, channel_id, message_ts,
        text="⏳ Posting to Rocketlane...",
        blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "⏳ *Posting to Rocketlane...*"}}],
    )

    try:
        from .post_time_entries import post_day
        from .rocketlane_client import populate_overhead_phase_ids
        from .slack_notifier import build_blocks

        day = _load_day(date_str, user=user)
        populate_overhead_phase_ids()
        posted, failed = post_day(day, api_key=api_key)

        if posted == 0 and failed == 0:
            result_text = "✅ All entries already posted — nothing new to add."
        else:
            result_text = f"✅ Posted {posted} entr{'y' if posted == 1 else 'ies'} to Rocketlane."
            if failed:
                result_text += f" ({failed} failed — check logs)"

        # Rebuild the summary with the button removed and result appended
        blocks = build_blocks(day)
        # Remove the actions block (the "Post to Rocketlane" button)
        blocks = [b for b in blocks if b.get("type") != "actions"]
        # Replace the footer prompt with the result
        for b in blocks:
            text_obj = b.get("text", {})
            if isinstance(text_obj, dict) and "Reply in this thread" in text_obj.get("text", ""):
                text_obj["text"] = text_obj["text"].replace(
                    "Reply in this thread to correct classifications, or click the button to post.",
                    result_text,
                )
        _update_message(
            web_client, channel_id, message_ts,
            text=f"Time Summary — {date_str} (posted)",
            blocks=blocks,
        )

    except Exception as e:
        error_text = f"❌ Error posting to Rocketlane: {e}"
        _update_message(
            web_client, channel_id, message_ts,
            text=error_text,
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": error_text}}],
        )
        print(f"[handle_button] {error_text}")


# ---------------------------------------------------------------------------
# Message handler — thread replies for corrections
# ---------------------------------------------------------------------------

def handle_message(web_client, event: dict) -> None:
    # Only handle thread replies (thread_ts present and different from ts)
    thread_ts = event.get("thread_ts")
    ts = event.get("ts")
    if not thread_ts or thread_ts == ts:
        return

    # Ignore bot messages to prevent loops
    if event.get("bot_id") or event.get("subtype"):
        return

    channel_id = event.get("channel", "")
    text = (event.get("text") or "").strip()
    if not text:
        return

    # Look up original message in pending cache
    pending = _load_pending()
    entry = pending.get(thread_ts)
    if not entry:
        return  # Not a time-tracking thread

    date_str = entry["date"]
    user = _resolve_user(entry)
    api_key = user.rocketlane_api_key if user else None

    try:
        from .correction_interpreter import interpret_and_apply
        from .slack_notifier import build_blocks

        day = _load_day(date_str, user=user)
        updated_day, summary, save_as_rule, changes = interpret_and_apply(day, text)
        _save_day(updated_day, user=user)

        # Persist corrections to per-user memory for future replay
        if user and changes:
            from .correction_memory import upsert_memories
            upsert_memories(user.user_id, changes, text)

        # Auto-post to Rocketlane
        try:
            from .post_time_entries import post_day
            posted, skipped = post_day(updated_day, api_key=api_key)
            post_note = f"\n✓ {posted} entr{'y' if posted == 1 else 'ies'} posted to Rocketlane ({skipped} already existed)"
        except Exception as post_err:
            post_note = f"\n⚠️ Rocketlane post failed: {post_err} — changes saved locally"

        # Rebuild the original message with the updated table
        blocks = build_blocks(updated_day)
        _update_message(
            web_client, channel_id, thread_ts,
            text=f"Time Summary — {date_str} (updated)",
            blocks=blocks,
        )

        # Thread reply confirming the change
        reply = f"✓ {summary}{post_note}"
        if save_as_rule:
            reply += "\n✓ Rule saved and pushed to GitHub"

        web_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=reply,
        )

    except Exception as e:
        web_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=f"❌ Error applying correction: {e}",
        )
        print(f"[handle_message] Error: {e}")


# ---------------------------------------------------------------------------
# Main request dispatcher
# ---------------------------------------------------------------------------

def handle_request(socket_client, req, web_client) -> None:
    from slack_sdk.socket_mode.response import SocketModeResponse

    # Acknowledge every request immediately (Slack requires <3s)
    socket_client.send_socket_mode_response(
        SocketModeResponse(envelope_id=req.envelope_id)
    )

    if req.type == "interactive":
        payload = req.payload
        if payload.get("type") == "block_actions":
            actions = payload.get("actions", [])
            if actions and actions[0].get("action_id") == "post_to_rocketlane":
                handle_button(web_client, payload)

    elif req.type == "events_api":
        event = req.payload.get("event", {})
        if event.get("type") == "message":
            handle_message(web_client, event)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    load_dotenv()

    app_token = os.environ.get("SLACK_APP_TOKEN")
    bot_token = os.environ.get("SLACK_BOT_TOKEN")

    if not app_token:
        print(
            "Error: SLACK_APP_TOKEN not set.\n"
            "  1. Slack app dashboard → Settings > Socket Mode → Enable\n"
            "  2. Create App-Level Token with scope 'connections:write'\n"
            "  3. Add SLACK_APP_TOKEN=xapp-... to .env"
        )
        sys.exit(1)
    if not bot_token:
        print("Error: SLACK_BOT_TOKEN not set in .env")
        sys.exit(1)

    try:
        from slack_sdk import WebClient
        from slack_sdk.socket_mode import SocketModeClient
    except ImportError:
        print("Error: slack-sdk not installed. Run: uv add slack-sdk")
        sys.exit(1)

    web_client = WebClient(token=bot_token)
    socket_client = SocketModeClient(
        app_token=app_token,
        web_client=web_client,
    )

    socket_client.socket_mode_request_listeners.append(
        lambda sc, req: handle_request(sc, req, web_client)
    )

    socket_client.connect()
    print("Time tracking listener running... (Ctrl+C to stop)")
    print(f"  Pending cache: {_PENDING_FILE}")

    try:
        Event().wait()
    except KeyboardInterrupt:
        print("\nStopping listener.")
        socket_client.close()


if __name__ == "__main__":
    main()
