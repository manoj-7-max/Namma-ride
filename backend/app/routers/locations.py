from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import Principal, require_role, utc_now
from app.config import get_settings
from app.database import get_db
from app.models import DriverLocation, Ride
from app.routers.rides import approved_driver
from app.schemas import (
    DriverLocationOut,
    DriverLocationUpdate,
    NearbyDriverSummary,
)
from app.services import current_driver_candidates

router = APIRouter(prefix="/api/v1", tags=["locations"])


@router.put("/driver/location", response_model=DriverLocationOut)
def update_driver_location(
    payload: DriverLocationUpdate,
    principal: Principal = Depends(approved_driver),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    now = utc_now()
    captured_at = payload.captured_at.replace(tzinfo=None)
    if captured_at < now - timedelta(seconds=settings.location_max_age_seconds):
        raise HTTPException(422, "Location timestamp is stale")
    if captured_at > now + timedelta(seconds=30):
        raise HTTPException(422, "Location timestamp is in the future")
    if payload.accuracy_m > settings.location_max_accuracy_m:
        raise HTTPException(422, "Location accuracy is insufficient")
    location = db.get(DriverLocation, principal.user.id)
    if (
        location
        and payload.available
        and location.updated_at
        > now - timedelta(seconds=settings.location_min_interval_seconds)
    ):
        raise HTTPException(429, "Location update rate limit exceeded")
    if location is None:
        location = DriverLocation(driver_id=principal.user.id)
        db.add(location)
    location.latitude = payload.latitude
    location.longitude = payload.longitude
    location.accuracy_m = payload.accuracy_m
    location.captured_at = captured_at
    location.available = payload.available
    location.updated_at = now
    db.commit()
    db.refresh(location)
    return location


@router.get("/drivers/nearby", response_model=NearbyDriverSummary)
def nearby_drivers(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    _: Principal = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    candidates = current_driver_candidates(db, latitude, longitude)
    return NearbyDriverSummary(
        available_count=len(candidates),
        nearest_distance_km=round(candidates[0][2], 2) if candidates else None,
        radius_km=get_settings().matching_radius_km,
    )


@router.get("/rides/{ride_id}/driver-location", response_model=DriverLocationOut)
def assigned_driver_location(
    ride_id: int,
    principal: Principal = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    ride = db.scalar(select(Ride).where(Ride.id == ride_id))
    if not ride or ride.customer_id != principal.user.id:
        raise HTTPException(404, "Ride not found")
    if ride.status not in {"accepted", "arrived", "started"} or not ride.driver_id:
        raise HTTPException(403, "Driver tracking is not available for this ride")
    location = db.get(DriverLocation, ride.driver_id)
    if not location:
        raise HTTPException(404, "Driver location is not available")
    return location
