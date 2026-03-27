from __future__ import annotations

from fastapi import APIRouter

from .. import mbta_client
from ..models import RouteInfo, StopInfo

router = APIRouter(prefix="/api", tags=["stops"])


@router.get("/routes")
async def get_routes() -> list[RouteInfo]:
    return await mbta_client.get_routes()


@router.get("/stops/{route_id}")
async def get_stops(route_id: str) -> list[StopInfo]:
    return await mbta_client.get_stops(route_id)
