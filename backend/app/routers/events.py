import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Principal, require_role
from app.database import get_db, get_engine
from app.models import Ride, RideEvent
from app.schemas import RideEventOut

router = APIRouter(prefix="/api/v1/rides", tags=["ride events"])


def authorize(ride: Ride | None, principal: Principal):
    if ride is None:
        raise HTTPException(404, "Ride not found")
    if principal.role == "customer" and ride.customer_id != principal.user.id:
        raise HTTPException(403, "Ride access denied")
    if principal.role == "driver" and ride.driver_id != principal.user.id:
        raise HTTPException(403, "Ride access denied")


@router.get("/{ride_id}/events", response_model=list[RideEventOut])
def ride_events(
    ride_id: int,
    after_id: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_role("customer", "driver", "admin")),
    db: Session = Depends(get_db),
):
    authorize(db.get(Ride, ride_id), principal)
    return db.scalars(
        select(RideEvent)
        .where(RideEvent.ride_id == ride_id, RideEvent.id > after_id)
        .order_by(RideEvent.id)
    ).all()


@router.get("/{ride_id}/events/stream")
async def stream_ride_events(
    ride_id: int,
    request: Request,
    after_id: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_role("customer", "driver", "admin")),
    db: Session = Depends(get_db),
):
    authorize(db.get(Ride, ride_id), principal)

    async def generate():
        cursor = after_id
        for _ in range(60):
            if await request.is_disconnected():
                break
            with Session(get_engine()) as session:
                events = session.scalars(
                    select(RideEvent)
                    .where(RideEvent.ride_id == ride_id, RideEvent.id > cursor)
                    .order_by(RideEvent.id)
                ).all()
                for event in events:
                    cursor = event.id
                    payload = {
                        "id": event.id,
                        "event_type": event.event_type,
                        "detail": event.detail,
                        "created_at": event.created_at.isoformat(),
                    }
                    yield f"id: {event.id}\ndata: {json.dumps(payload)}\n\n"
            yield ": keep-alive\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(generate(), media_type="text/event-stream")
