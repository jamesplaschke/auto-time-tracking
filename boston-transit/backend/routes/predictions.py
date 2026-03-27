from __future__ import annotations

from fastapi import APIRouter, Query

from .. import mbta_client
from ..models import Prediction

router = APIRouter(prefix="/api", tags=["predictions"])


@router.get("/predictions")
async def get_predictions(
    stops: str = Query(..., description="Comma-separated stop IDs"),
    routes: str | None = Query(None, description="Comma-separated route IDs"),
) -> list[Prediction]:
    stop_ids = [s.strip() for s in stops.split(",") if s.strip()]
    route_ids = [r.strip() for r in routes.split(",") if r.strip()] if routes else None
    return await mbta_client.get_predictions(stop_ids, route_ids)
