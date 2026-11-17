from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Ride, User
from app.schemas import DriverOut, RideOut

BASE_FARE_PAISE = 5000
PER_KM_PAISE = 1500


def fare_for(distance_tenths_km: int) -> int:
    return BASE_FARE_PAISE + (distance_tenths_km * PER_KM_PAISE + 5) // 10


def ride_out(ride: Ride) -> RideOut:
    driver = None
    if ride.driver:
        driver = DriverOut(
            id=ride.driver.id,
            display_name=ride.driver.display_name,
            phone=ride.driver.phone,
            vehicle_number=ride.driver.vehicle_number,
            approved=ride.driver.driver_approved,
        )
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
    )


def count_role(db: Session, role: str) -> int:
    return (
        db.scalar(select(func.count()).select_from(User).where(User.role == role)) or 0
    )
