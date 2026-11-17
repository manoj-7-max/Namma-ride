from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import utc_now
from app.config import get_settings
from app.models import DriverLocation, Ride, RideDispatch, RideEvent, User
from app.schemas import DriverLocationOut, DriverOut, RideOut

BASE_FARE_PAISE = 5000
PER_KM_PAISE = 1500


def fare_for(distance_tenths_km: int) -> int:
    return BASE_FARE_PAISE + (distance_tenths_km * PER_KM_PAISE + 5) // 10


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0088
    d_lat, d_lon = radians(lat2 - lat1), radians(lon2 - lon1)
    value = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(value))


def current_driver_candidates(
    db: Session, latitude: float, longitude: float, *, lock: bool = False
):
    settings = get_settings()
    cutoff = utc_now() - timedelta(seconds=settings.location_max_age_seconds)
    statement = (
        select(DriverLocation, User)
        .join(User, User.id == DriverLocation.driver_id)
        .where(
            User.driver_approved.is_(True),
            DriverLocation.available.is_(True),
            DriverLocation.captured_at >= cutoff,
            DriverLocation.accuracy_m <= settings.location_max_accuracy_m,
        )
    )
    if lock:
        statement = statement.with_for_update(skip_locked=True)
    rows = db.execute(statement).all()
    busy_driver_ids = set(
        db.scalars(
            select(Ride.driver_id).where(
                Ride.driver_id.is_not(None),
                Ride.status.in_(["accepted", "arrived", "started"]),
            )
        )
    )
    busy_driver_ids.update(
        db.scalars(
            select(RideDispatch.driver_id).where(
                RideDispatch.status == "offered",
                RideDispatch.expires_at > utc_now(),
            )
        )
    )
    candidates = [
        (
            location,
            user,
            haversine_km(latitude, longitude, location.latitude, location.longitude),
        )
        for location, user in rows
        if user.id not in busy_driver_ids
    ]
    return sorted(
        (
            candidate
            for candidate in candidates
            if candidate[2] <= settings.matching_radius_km
        ),
        key=lambda candidate: candidate[2],
    )


def add_event(db: Session, ride: Ride, event_type: str, detail: str | None = None):
    db.add(RideEvent(ride_id=ride.id, event_type=event_type, detail=detail))


def offer_next_driver(db: Session, ride: Ride) -> RideDispatch | None:
    if ride.pickup_latitude is None or ride.pickup_longitude is None:
        return None
    already_tried = set(
        db.scalars(
            select(RideDispatch.driver_id).where(RideDispatch.ride_id == ride.id)
        )
    )
    for _, driver, distance in current_driver_candidates(
        db, ride.pickup_latitude, ride.pickup_longitude, lock=True
    ):
        if driver.id in already_tried:
            continue
        dispatch = RideDispatch(
            ride_id=ride.id,
            driver_id=driver.id,
            status="offered",
            distance_m=round(distance * 1000),
            expires_at=utc_now()
            + timedelta(seconds=get_settings().dispatch_offer_seconds),
        )
        ride.status = "matching"
        db.add(dispatch)
        add_event(
            db, ride, "driver_offered", f"Offer {dispatch.expires_at.isoformat()}"
        )
        return dispatch
    ride.status = "no_driver_available"
    add_event(db, ride, "no_driver_available")
    return None


def expire_and_retry(db: Session, ride: Ride):
    active = db.scalar(
        select(RideDispatch)
        .where(RideDispatch.ride_id == ride.id, RideDispatch.status == "offered")
        .order_by(RideDispatch.id.desc())
    )
    if active and active.expires_at <= utc_now():
        active.status = "expired"
        add_event(db, ride, "offer_expired")
        offer_next_driver(db, ride)


def ride_out(ride: Ride, *, include_location: bool = True) -> RideOut:
    driver = None
    if ride.driver:
        driver = DriverOut(
            id=ride.driver.id,
            display_name=ride.driver.display_name,
            phone=ride.driver.phone,
            vehicle_number=ride.driver.vehicle_number,
            approved=ride.driver.driver_approved,
            suspended=ride.driver.driver_suspended,
        )
    visible_location = None
    eta = None
    if (
        include_location
        and ride.driver
        and ride.driver.location
        and ride.status
        in {
            "accepted",
            "arrived",
            "started",
        }
    ):
        location = ride.driver.location
        visible_location = DriverLocationOut(
            latitude=location.latitude,
            longitude=location.longitude,
            accuracy_m=location.accuracy_m,
            captured_at=location.captured_at,
            available=location.available,
            updated_at=location.updated_at,
        )
        if ride.pickup_latitude is not None:
            distance = haversine_km(
                location.latitude,
                location.longitude,
                ride.pickup_latitude,
                ride.pickup_longitude,
            )
            eta = max(1, round(distance / 20 * 60))
    return RideOut(
        id=ride.id,
        pickup=ride.pickup,
        dropoff=ride.dropoff,
        estimated_distance_km=ride.distance_tenths_km / 10,
        estimated_fare_paise=ride.estimated_fare_paise,
        estimated_fare_rupees=ride.estimated_fare_paise / 100,
        status=ride.status,
        customer_id=ride.customer_id,
        driver=driver,
        cancellation_reason=ride.cancellation_reason,
        created_at=ride.created_at,
        pickup_latitude=ride.pickup_latitude,
        pickup_longitude=ride.pickup_longitude,
        dropoff_latitude=ride.dropoff_latitude,
        dropoff_longitude=ride.dropoff_longitude,
        matching_state=ride.status
        if ride.status in {"matching", "no_driver_available"}
        else None,
        driver_location=visible_location,
        driver_eta_minutes=eta,
    )


def count_role(db: Session, role: str) -> int:
    return (
        db.scalar(select(func.count()).select_from(User).where(User.role == role)) or 0
    )
