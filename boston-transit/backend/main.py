from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from . import mbta_client
from .leave_now import compute_leave_now_alerts
from .models import StopPreference
from .routes import alerts, predictions, stops

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Never Miss the T", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions.router)
app.include_router(alerts.router)
app.include_router(stops.router)


@app.get("/api/stream")
async def stream_predictions(
    request: Request,
    stops: str = Query(..., description="Comma-separated stop IDs"),
    routes: str | None = Query(None, description="Comma-separated route IDs"),
    walk_times: str | None = Query(None, description="JSON-encoded walk times: {stop_id: minutes}"),
):
    """SSE endpoint that streams live predictions and leave-now alerts."""
    stop_ids = [s.strip() for s in stops.split(",") if s.strip()]
    route_ids = [r.strip() for r in routes.split(",") if r.strip()] if routes else None

    walk_prefs: list[StopPreference] = []
    if walk_times:
        try:
            wt = json.loads(walk_times)
            for sid, mins in wt.items():
                walk_prefs.append(StopPreference(stop_id=sid, walk_minutes=int(mins)))
        except (json.JSONDecodeError, ValueError):
            pass

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            try:
                preds = await mbta_client.get_predictions(stop_ids, route_ids)
                yield {
                    "event": "predictions",
                    "data": json.dumps(
                        [p.model_dump(mode="json") for p in preds]
                    ),
                }

                if walk_prefs:
                    leave_alerts = compute_leave_now_alerts(
                        preds, walk_prefs, datetime.now(timezone.utc)
                    )
                    yield {
                        "event": "leave_now",
                        "data": json.dumps(
                            [a.model_dump(mode="json") for a in leave_alerts]
                        ),
                    }

                alert_list = await mbta_client.get_alerts(route_ids)
                yield {
                    "event": "alerts",
                    "data": json.dumps(
                        [a.model_dump(mode="json") for a in alert_list]
                    ),
                }
            except Exception:
                logger.exception("Error fetching MBTA data")

            await asyncio.sleep(15)

    return EventSourceResponse(event_generator())


# Serve frontend static files
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        file_path = FRONTEND_DIST / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")


def run():
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
