from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import Principal, require_role
from app.database import get_db
from app.models import Ride, User
from app.schemas import ApprovalUpdate, DriverOut, RideOut
from app.services import count_role, ride_out

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


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
    db.commit()
    db.refresh(driver)
    return DriverOut(
        id=driver.id,
        display_name=driver.display_name,
        phone=driver.phone,
        vehicle_number=driver.vehicle_number,
        approved=driver.driver_approved,
    )


@router.get("/rides", response_model=list[RideOut])
def rides(_: Principal = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return [
        ride_out(ride)
        for ride in db.scalars(select(Ride).order_by(Ride.id.desc())).all()
    ]
