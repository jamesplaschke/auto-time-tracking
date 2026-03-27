from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class Prediction(BaseModel):
    id: str
    route_id: str
    route_name: str | None = None
    stop_id: str
    stop_name: str | None = None
    direction_id: int
    direction_name: str | None = None
    arrival_time: datetime | None = None
    departure_time: datetime | None = None
    status: str | None = None  # "Approaching", "1 stop away", etc.

    @property
    def time(self) -> datetime | None:
        return self.departure_time or self.arrival_time


class ServiceAlert(BaseModel):
    id: str
    header: str
    description: str = ""
    severity: int = 0
    affected_routes: list[str] = []
    affected_stops: list[str] = []
    active_period_start: datetime | None = None
    active_period_end: datetime | None = None
    url: str | None = None


class StopInfo(BaseModel):
    id: str
    name: str
    latitude: float = 0.0
    longitude: float = 0.0
    route_ids: list[str] = []


class RouteInfo(BaseModel):
    id: str
    name: str
    color: str = ""
    text_color: str = ""
    direction_names: list[str] = []


class LeaveNowAlert(BaseModel):
    stop_id: str
    stop_name: str
    route_id: str
    direction_id: int
    prediction_time: datetime
    walk_minutes: int
    leave_by: datetime
    urgency: str  # "now", "soon", "upcoming", "missed"
    minutes_until_leave: float


class StopPreference(BaseModel):
    stop_id: str
    route_id: str | None = None
    walk_minutes: int = 5
    enabled: bool = True


class StreamEvent(BaseModel):
    """Wrapper for SSE events sent to the frontend."""
    event_type: str  # "predictions", "alerts", "leave_now"
    data: list[Prediction] | list[ServiceAlert] | list[LeaveNowAlert]
