from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import Principal, require_role
from app.database import get_db
from app.models import Ride, RideRejection
from app.schemas import RideCreate, RideOut, RideStatusUpdate
from app.services import fare_for, ride_out

router = APIRouter(prefix="/api/v1", tags=["rides"])


def approved_driver(
    principal: Principal = Depends(require_role("driver")),
) -> Principal:
    if not principal.user or not principal.user.driver_approved:
        raise HTTPException(403, "Driver approval is required")
    return principal


@router.post("/rides", response_model=RideOut, status_code=201)
def create_ride(
    payload: RideCreate,
    principal: Principal = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    distance = round(payload.estimated_distance_km * 10)
    ride = Ride(
        customer_id=principal.user.id,
        pickup=payload.pickup.strip(),
        dropoff=payload.dropoff.strip(),
        distance_tenths_km=distance,
        estimated_fare_paise=fare_for(distance),
        status="requested",
    )
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride_out(ride)


@router.get("/rides/mine", response_model=list[RideOut])
def my_rides(
    principal: Principal = Depends(require_role("customer", "driver")),
    db: Session = Depends(get_db),
):
    condition = (
        Ride.customer_id == principal.user.id
        if principal.role == "customer"
        else Ride.driver_id == principal.user.id
    )
    return [
        ride_out(ride)
        for ride in db.scalars(
            select(Ride).where(condition).order_by(Ride.id.desc())
        ).all()
    ]


@router.get("/rides/{ride_id}", response_model=RideOut)
def get_ride(
    ride_id: int,
    principal: Principal = Depends(require_role("customer", "driver", "admin")),
    db: Session = Depends(get_db),
):
    ride = db.get(Ride, ride_id)
    if ride is None:
        raise HTTPException(404, "Ride not found")
    if principal.role == "customer" and ride.customer_id != principal.user.id:
        raise HTTPException(403, "Ride does not belong to this customer")
    if principal.role == "driver" and ride.driver_id != principal.user.id:
        raise HTTPException(403, "Ride does not belong to this driver")
    return ride_out(ride)


@router.get("/driver/requests", response_model=list[RideOut])
def ride_requests(
    principal: Principal = Depends(approved_driver), db: Session = Depends(get_db)
):
    rejected = select(RideRejection.ride_id).where(
        RideRejection.driver_id == principal.user.id
    )
    rides = db.scalars(
        select(Ride)
        .where(
            Ride.status == "requested",
            Ride.driver_id.is_(None),
            Ride.id.not_in(rejected),
        )
        .order_by(Ride.id)
    ).all()
    return [ride_out(ride) for ride in rides]


@router.post("/driver/requests/{ride_id}/accept", response_model=RideOut)
def accept_ride(
    ride_id: int,
    principal: Principal = Depends(approved_driver),
    db: Session = Depends(get_db),
):
    result = db.execute(
        update(Ride)
        .where(Ride.id == ride_id, Ride.status == "requested", Ride.driver_id.is_(None))
        .values(driver_id=principal.user.id, status="accepted")
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Ride is no longer available")
    db.commit()
    return ride_out(db.get(Ride, ride_id))


@router.post("/driver/requests/{ride_id}/reject", status_code=204)
def reject_ride(
    ride_id: int,
    principal: Principal = Depends(approved_driver),
    db: Session = Depends(get_db),
):
    ride = db.get(Ride, ride_id)
    if ride is None or ride.status != "requested":
        raise HTTPException(409, "Ride is no longer available")
    db.add(RideRejection(ride_id=ride_id, driver_id=principal.user.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return None


@router.patch("/rides/{ride_id}/status", response_model=RideOut)
def update_status(
    ride_id: int,
    payload: RideStatusUpdate,
    principal: Principal = Depends(require_role("customer", "driver", "admin")),
    db: Session = Depends(get_db),
):
    ride = db.get(Ride, ride_id)
    if ride is None:
        raise HTTPException(404, "Ride not found")
    if payload.status == "cancelled":
        customer_allowed = (
            principal.role == "customer"
            and ride.customer_id == principal.user.id
            and ride.status in {"requested", "accepted"}
        )
        driver_allowed = (
            principal.role == "driver"
            and ride.driver_id == principal.user.id
            and ride.status in {"accepted", "arrived"}
        )
        if not (
            customer_allowed or driver_allowed or principal.role == "admin"
        ) or ride.status in {"completed", "cancelled"}:
            raise HTTPException(409, "Ride cannot be cancelled in its current state")
        ride.status = "cancelled"
        ride.cancellation_reason = payload.cancellation_reason or "Cancelled by user"
    else:
        if (
            principal.role != "driver"
            or ride.driver_id != principal.user.id
            or not principal.user.driver_approved
        ):
            raise HTTPException(
                403, "Only the approved assigned driver can advance this ride"
            )
        transitions = {
            "accepted": "arrived",
            "arrived": "started",
            "started": "completed",
        }
        if transitions.get(ride.status) != payload.status:
            raise HTTPException(409, "Invalid ride status transition")
        ride.status = payload.status
    db.commit()
    db.refresh(ride)
    return ride_out(ride)
