from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import LeaveNowAlert, Prediction, StopPreference


def compute_leave_now_alerts(
    predictions: list[Prediction],
    preferences: list[StopPreference],
    now: datetime | None = None,
) -> list[LeaveNowAlert]:
    """Compute leave-now alerts for predictions based on walk times."""
    if now is None:
        now = datetime.now(timezone.utc)

    # Build lookup: stop_id -> walk_minutes
    walk_times: dict[str, int] = {}
    for pref in preferences:
        if pref.walk_minutes > 0:
            walk_times[pref.stop_id] = pref.walk_minutes

    alerts = []
    for pred in predictions:
        walk_min = walk_times.get(pred.stop_id)
        if walk_min is None:
            continue

        pred_time = pred.time
        if pred_time is None:
            continue

        # Ensure timezone-aware comparison
        if pred_time.tzinfo is None:
            pred_time = pred_time.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        leave_by = pred_time - timedelta(minutes=walk_min)
        time_until_leave = (leave_by - now).total_seconds()
        minutes_until = time_until_leave / 60

        if time_until_leave <= 0:
            urgency = "missed"
        elif time_until_leave <= 60:
            urgency = "now"
        elif time_until_leave <= 300:  # 5 min
            urgency = "soon"
        elif time_until_leave <= 900:  # 15 min
            urgency = "upcoming"
        else:
            continue  # Too far out, skip

        alerts.append(LeaveNowAlert(
            stop_id=pred.stop_id,
            stop_name=pred.stop_name or pred.stop_id,
            route_id=pred.route_id,
            direction_id=pred.direction_id,
            prediction_time=pred_time,
            walk_minutes=walk_min,
            leave_by=leave_by,
            urgency=urgency,
            minutes_until_leave=round(minutes_until, 1),
        ))

    # Sort: most urgent first
    urgency_order = {"now": 0, "soon": 1, "upcoming": 2, "missed": 3}
    alerts.sort(key=lambda a: (urgency_order.get(a.urgency, 9), a.minutes_until_leave))
    return alerts
