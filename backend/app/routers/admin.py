from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import Principal, require_role, utc_now
from app.config import get_settings
from app.database import get_db
from app.models import AuditLog, DriverLocation, Ride, RideEvent, User
from app.schemas import (
    ActiveUpdate,
    ApprovalUpdate,
    CustomerOut,
    DriverOut,
    RideOut,
    SuspensionUpdate,
)
from app.services import count_role, ride_out

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def audit(
    db: Session,
    action: str,
    target_type: str,
    target_id: int | None,
    detail: str | None = None,
):
    db.add(
        AuditLog(
            actor_role="admin",
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )


@router.get("/summary")
def summary(
    _: Principal = Depends(require_role("admin")), db: Session = Depends(get_db)
):
    return {
        "customers": count_role(db, "customer"),
        "drivers": count_role(db, "driver"),
        "pending_drivers": db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == "driver", User.driver_approved.is_(False))
        )
        or 0,
        "rides": db.scalar(select(func.count()).select_from(Ride)) or 0,
        "online_drivers": db.scalar(
            select(func.count())
            .select_from(DriverLocation)
            .where(
                DriverLocation.available.is_(True),
                DriverLocation.captured_at
                >= utc_now()
                - timedelta(seconds=get_settings().location_max_age_seconds),
            )
        )
        or 0,
        "active_rides": db.scalar(
            select(func.count())
            .select_from(Ride)
            .where(Ride.status.in_(["matching", "accepted", "arrived", "started"]))
        )
        or 0,
        "customer_limit": 100,
        "driver_limit": 10,
    }


@router.get("/drivers", response_model=list[DriverOut])
def drivers(
    _: Principal = Depends(require_role("admin")), db: Session = Depends(get_db)
):
    return [
        DriverOut(
            id=user.id,
            display_name=user.display_name,
            phone=user.phone,
            vehicle_number=user.vehicle_number,
            approved=user.driver_approved,
            suspended=user.driver_suspended,
        )
        for user in db.scalars(
            select(User).where(User.role == "driver").order_by(User.id)
        ).all()
    ]


@router.patch("/drivers/{driver_id}/approval", response_model=DriverOut)
def approve_driver(
    driver_id: int,
    payload: ApprovalUpdate,
    _: Principal = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    driver = db.get(User, driver_id)
    if driver is None or driver.role != "driver":
        raise HTTPException(404, "Driver not found")
    driver.driver_approved = payload.approved
    audit(db, "driver.approval_changed", "driver", driver.id, str(payload.approved))
    db.commit()
    db.refresh(driver)
    return DriverOut(
        id=driver.id,
        display_name=driver.display_name,
        phone=driver.phone,
        vehicle_number=driver.vehicle_number,
        approved=driver.driver_approved,
        suspended=driver.driver_suspended,
    )


@router.patch("/drivers/{driver_id}/suspension", response_model=DriverOut)
def suspend_driver(
    driver_id: int,
    payload: SuspensionUpdate,
    _: Principal = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    driver = db.get(User, driver_id)
    if driver is None or driver.role != "driver":
        raise HTTPException(404, "Driver not found")
    driver.driver_suspended = payload.suspended
    if payload.suspended and driver.location:
        driver.location.available = False
    audit(db, "driver.suspension_changed", "driver", driver.id, str(payload.suspended))
    db.commit()
    db.refresh(driver)
    return DriverOut(
        id=driver.id,
        display_name=driver.display_name,
        phone=driver.phone,
        vehicle_number=driver.vehicle_number,
        approved=driver.driver_approved,
        suspended=driver.driver_suspended,
    )


@router.get("/customers", response_model=list[CustomerOut])
def customers(
    _: Principal = Depends(require_role("admin")), db: Session = Depends(get_db)
):
    return [
        CustomerOut(
            id=user.id,
            display_name=user.display_name,
            phone=user.phone,
            active=user.is_active,
            created_at=user.created_at,
        )
        for user in db.scalars(
            select(User).where(User.role == "customer").order_by(User.id)
        ).all()
    ]


@router.patch("/customers/{customer_id}/active", response_model=CustomerOut)
def set_customer_active(
    customer_id: int,
    payload: ActiveUpdate,
    _: Principal = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    customer = db.get(User, customer_id)
    if customer is None or customer.role != "customer":
        raise HTTPException(404, "Customer not found")
    customer.is_active = payload.active
    audit(db, "customer.active_changed", "customer", customer.id, str(payload.active))
    db.commit()
    db.refresh(customer)
    return CustomerOut(
        id=customer.id,
        display_name=customer.display_name,
        phone=customer.phone,
        active=customer.is_active,
        created_at=customer.created_at,
    )


@router.get("/audit")
def audit_logs(
    _: Principal = Depends(require_role("admin")), db: Session = Depends(get_db)
):
    return [
        {
            "id": entry.id,
            "action": entry.action,
            "target_type": entry.target_type,
            "target_id": entry.target_id,
            "detail": entry.detail,
            "created_at": entry.created_at,
        }
        for entry in db.scalars(
            select(AuditLog).order_by(AuditLog.id.desc()).limit(100)
        ).all()
    ]


@router.get("/rides", response_model=list[RideOut])
def rides(_: Principal = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return [
        ride_out(ride, include_location=False)
        for ride in db.scalars(select(Ride).order_by(Ride.id.desc())).all()
    ]


@router.get("/operations")
def operations(
    _: Principal = Depends(require_role("admin")), db: Session = Depends(get_db)
):
    drivers = db.execute(
        select(User, DriverLocation)
        .join(DriverLocation, DriverLocation.driver_id == User.id, isouter=True)
        .where(User.role == "driver")
        .order_by(User.id)
    ).all()
    failures = db.scalars(
        select(RideEvent)
        .where(RideEvent.event_type.in_(["offer_expired", "no_driver_available"]))
        .order_by(RideEvent.id.desc())
        .limit(20)
    ).all()
    return {
        "drivers": [
            {
                "id": user.id,
                "display_name": user.display_name,
                "vehicle_number": user.vehicle_number,
                "approved": user.driver_approved,
                "available": bool(location and location.available),
                "last_location_at": location.captured_at if location else None,
            }
            for user, location in drivers
        ],
        "active_rides": [
            {
                "id": ride.id,
                "status": ride.status,
                "driver_id": ride.driver_id,
                "updated_at": ride.updated_at,
            }
            for ride in db.scalars(
                select(Ride)
                .where(Ride.status.in_(["matching", "accepted", "arrived", "started"]))
                .order_by(Ride.id.desc())
            ).all()
        ],
        "failures": [
            {
                "ride_id": event.ride_id,
                "type": event.event_type,
                "created_at": event.created_at,
            }
            for event in failures
        ],
    }
