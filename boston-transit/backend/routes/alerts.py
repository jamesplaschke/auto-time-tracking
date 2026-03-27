from __future__ import annotations

from fastapi import APIRouter, Query

from .. import mbta_client
from ..models import ServiceAlert

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get("/alerts")
async def get_alerts(
    routes: str | None = Query(None, description="Comma-separated route IDs"),
) -> list[ServiceAlert]:
    route_ids = [r.strip() for r in routes.split(",") if r.strip()] if routes else None
    return await mbta_client.get_alerts(route_ids)
