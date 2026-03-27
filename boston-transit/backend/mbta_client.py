from __future__ import annotations

import os
from datetime import datetime

import httpx

from .models import Prediction, RouteInfo, ServiceAlert, StopInfo

MBTA_BASE_URL = "https://api-v3.mbta.com"

# Subway route types: 0 = Light Rail (Green), 1 = Heavy Rail (Red/Orange/Blue)
SUBWAY_ROUTE_TYPES = "0,1"


def _headers() -> dict[str, str]:
    key = os.getenv("MBTA_API_KEY", "")
    if key:
        return {"x-api-key": key}
    return {}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=MBTA_BASE_URL,
        headers=_headers(),
        timeout=15.0,
    )


def _parse_datetime(val: str | None) -> datetime | None:
    if not val:
        return None
    return datetime.fromisoformat(val)


# ---- Routes ----

async def get_routes() -> list[RouteInfo]:
    """Fetch all subway routes (Red, Orange, Blue, Green-*)."""
    async with _client() as client:
        resp = await client.get("/routes", params={"filter[type]": SUBWAY_ROUTE_TYPES})
        resp.raise_for_status()
        data = resp.json()

    routes = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        routes.append(RouteInfo(
            id=item["id"],
            name=attrs.get("long_name", "") or attrs.get("short_name", item["id"]),
            color=f"#{attrs['color']}" if attrs.get("color") else "",
            text_color=f"#{attrs['text_color']}" if attrs.get("text_color") else "",
            direction_names=attrs.get("direction_names", []),
        ))
    return routes


# ---- Stops ----

async def get_stops(route_id: str) -> list[StopInfo]:
    """Fetch stops for a given route."""
    async with _client() as client:
        resp = await client.get("/stops", params={"filter[route]": route_id})
        resp.raise_for_status()
        data = resp.json()

    stops = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        stops.append(StopInfo(
            id=item["id"],
            name=attrs.get("name", ""),
            latitude=attrs.get("latitude", 0.0) or 0.0,
            longitude=attrs.get("longitude", 0.0) or 0.0,
        ))
    return stops


# ---- Predictions ----

async def get_predictions(stop_ids: list[str], route_ids: list[str] | None = None) -> list[Prediction]:
    """Fetch real-time predictions for one or more stops."""
    params: dict[str, str] = {
        "filter[stop]": ",".join(stop_ids),
        "sort": "departure_time",
        "include": "route,stop",
    }
    if route_ids:
        params["filter[route]"] = ",".join(route_ids)

    async with _client() as client:
        resp = await client.get("/predictions", params=params)
        resp.raise_for_status()
        data = resp.json()

    # Build lookup maps from included resources
    included = data.get("included", [])
    route_map: dict[str, dict] = {}
    stop_map: dict[str, dict] = {}
    for inc in included:
        if inc["type"] == "route":
            route_map[inc["id"]] = inc.get("attributes", {})
        elif inc["type"] == "stop":
            stop_map[inc["id"]] = inc.get("attributes", {})

    predictions = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        rels = item.get("relationships", {})

        route_id = rels.get("route", {}).get("data", {}).get("id", "")
        stop_id = rels.get("stop", {}).get("data", {}).get("id", "")

        route_attrs = route_map.get(route_id, {})
        stop_attrs = stop_map.get(stop_id, {})

        arrival = _parse_datetime(attrs.get("arrival_time"))
        departure = _parse_datetime(attrs.get("departure_time"))

        # Skip predictions with no time info
        if not arrival and not departure:
            continue

        predictions.append(Prediction(
            id=item["id"],
            route_id=route_id,
            route_name=route_attrs.get("long_name") or route_attrs.get("short_name", ""),
            stop_id=stop_id,
            stop_name=stop_attrs.get("name", ""),
            direction_id=attrs.get("direction_id", 0),
            direction_name=attrs.get("direction_name", ""),
            arrival_time=arrival,
            departure_time=departure,
            status=attrs.get("status"),
        ))

    return predictions


# ---- Alerts ----

async def get_alerts(route_ids: list[str] | None = None) -> list[ServiceAlert]:
    """Fetch active service alerts for subway routes."""
    params: dict[str, str] = {
        "filter[activity]": "BOARD,EXIT,RIDE",
    }
    if route_ids:
        params["filter[route]"] = ",".join(route_ids)
    else:
        params["filter[route_type]"] = SUBWAY_ROUTE_TYPES

    async with _client() as client:
        resp = await client.get("/alerts", params=params)
        resp.raise_for_status()
        data = resp.json()

    alerts = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})

        affected_routes = []
        affected_stops = []
        for entity in attrs.get("informed_entity", []):
            if entity.get("route"):
                affected_routes.append(entity["route"])
            if entity.get("stop"):
                affected_stops.append(entity["stop"])

        header = ""
        description = ""
        url = None
        for hdr in attrs.get("header", "") if isinstance(attrs.get("header"), list) else [attrs.get("header", "")]:
            header = hdr
            break
        description = attrs.get("description", "") or ""
        url = attrs.get("url")

        active_start = None
        active_end = None
        periods = attrs.get("active_period", [])
        if periods:
            active_start = _parse_datetime(periods[0].get("start"))
            active_end = _parse_datetime(periods[0].get("end"))

        alerts.append(ServiceAlert(
            id=item["id"],
            header=header,
            description=description,
            severity=attrs.get("severity", 0) or 0,
            affected_routes=list(set(affected_routes)),
            affected_stops=list(set(affected_stops)),
            active_period_start=active_start,
            active_period_end=active_end,
            url=url,
        ))

    return alerts
