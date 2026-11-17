from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import Principal, require_role, utc_now
from app.database import get_db
from app.models import Ride, RideDispatch, RideRejection
from app.schemas import RideCreate, RideOut, RideStatusUpdate
from app.services import (
    add_event,
    expire_and_retry,
    fare_for,
    offer_next_driver,
    ride_out,
)

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
        pickup_latitude=payload.pickup_latitude,
        pickup_longitude=payload.pickup_longitude,
        dropoff_latitude=payload.dropoff_latitude,
        dropoff_longitude=payload.dropoff_longitude,
        distance_tenths_km=distance,
        estimated_fare_paise=fare_for(distance),
        status="requested",
    )
    db.add(ride)
    db.flush()
    add_event(db, ride, "ride_requested")
    if payload.pickup_latitude is not None:
        offer_next_driver(db, ride)
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
    matching = db.scalars(
        select(Ride).where(condition, Ride.status == "matching")
    ).all()
    for ride in matching:
        expire_and_retry(db, ride)
    db.commit()
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


@router.post("/rides/{ride_id}/rematch", response_model=RideOut)
def rematch_ride(
    ride_id: int,
    principal: Principal = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    ride = db.scalar(select(Ride).where(Ride.id == ride_id).with_for_update())
    if not ride or ride.customer_id != principal.user.id:
        raise HTTPException(404, "Ride not found")
    if ride.status != "no_driver_available":
        raise HTTPException(409, "Ride is not waiting for rematch")
    offer_next_driver(db, ride)
    db.commit()
    db.refresh(ride)
    return ride_out(ride)


@router.get("/driver/requests", response_model=list[RideOut])
def ride_requests(
    principal: Principal = Depends(approved_driver), db: Session = Depends(get_db)
):
    for ride in db.scalars(select(Ride).where(Ride.status == "matching")).all():
        expire_and_retry(db, ride)
    db.commit()
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
    offered_ids = select(RideDispatch.ride_id).where(
        RideDispatch.driver_id == principal.user.id,
        RideDispatch.status == "offered",
        RideDispatch.expires_at > utc_now(),
    )
    offered = db.scalars(select(Ride).where(Ride.id.in_(offered_ids))).all()
    return [ride_out(ride) for ride in [*offered, *rides]]


@router.post("/driver/requests/{ride_id}/accept", response_model=RideOut)
def accept_ride(
    ride_id: int,
    principal: Principal = Depends(approved_driver),
    db: Session = Depends(get_db),
):
    ride = db.scalar(select(Ride).where(Ride.id == ride_id).with_for_update())
    if (
        not ride
        or ride.driver_id is not None
        or ride.status
        not in {
            "requested",
            "matching",
        }
    ):
        raise HTTPException(409, "Ride is no longer available")
    dispatch = db.scalar(
        select(RideDispatch)
        .where(
            RideDispatch.ride_id == ride_id,
            RideDispatch.driver_id == principal.user.id,
            RideDispatch.status == "offered",
        )
        .with_for_update()
    )
    if ride.status == "matching" and (
        dispatch is None or dispatch.expires_at <= utc_now()
    ):
        raise HTTPException(409, "Dispatch offer expired or was not assigned to driver")
    ride.driver_id = principal.user.id
    ride.status = "accepted"
    if dispatch:
        dispatch.status = "accepted"
    db.execute(
        update(RideDispatch)
        .where(RideDispatch.ride_id == ride_id, RideDispatch.status == "offered")
        .values(status="expired")
    )
    if dispatch:
        dispatch.status = "accepted"
    add_event(db, ride, "ride_accepted")
    db.commit()
    return ride_out(db.get(Ride, ride_id))


@router.post("/driver/requests/{ride_id}/reject", status_code=204)
def reject_ride(
    ride_id: int,
    principal: Principal = Depends(approved_driver),
    db: Session = Depends(get_db),
):
    ride = db.get(Ride, ride_id)
    if ride is None or ride.status not in {"requested", "matching"}:
        raise HTTPException(409, "Ride is no longer available")
    dispatch = db.scalar(
        select(RideDispatch).where(
            RideDispatch.ride_id == ride_id,
            RideDispatch.driver_id == principal.user.id,
            RideDispatch.status == "offered",
        )
    )
    if ride.status == "matching" and dispatch is None:
        raise HTTPException(403, "Ride offer is not assigned to this driver")
    if dispatch:
        dispatch.status = "rejected"
        add_event(db, ride, "driver_rejected")
    db.add(RideRejection(ride_id=ride_id, driver_id=principal.user.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    if dispatch:
        offer_next_driver(db, ride)
        db.commit()
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
            and ride.status
            in {"requested", "matching", "no_driver_available", "accepted"}
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
    add_event(db, ride, f"ride_{ride.status}", ride.cancellation_reason)
    db.commit()
    db.refresh(ride)
    return ride_out(ride)
