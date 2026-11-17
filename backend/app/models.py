from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PilotMember(Base):
    """Phase 1 compatibility table; new identities are stored in users."""

    __tablename__ = "pilot_members"
    __table_args__ = (
        CheckConstraint("role IN ('customer', 'driver')", name="valid_pilot_role"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(10))
    display_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('customer', 'driver')", name="valid_user_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(10), index=True)
    driver_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    driver_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    vehicle_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())

    location: Mapped["DriverLocation | None"] = relationship(
        back_populates="driver", uselist=False
    )


class OTPChallenge(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(13), index=True)
    role: Mapped[str] = mapped_column(String(10))
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime())
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())


class Ride(Base):
    __tablename__ = "rides"
    __table_args__ = (
        CheckConstraint(
            "status IN ('requested','matching','no_driver_available','accepted','arrived','started','completed','cancelled')",
            name="valid_ride_status",
        ),
        CheckConstraint("estimated_fare_paise >= 0", name="nonnegative_fare"),
        CheckConstraint("distance_tenths_km > 0", name="positive_distance"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    driver_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    pickup: Mapped[str] = mapped_column(String(200))
    dropoff: Mapped[str] = mapped_column(String(200))
    pickup_latitude: Mapped[float | None] = mapped_column(Float(), nullable=True)
    pickup_longitude: Mapped[float | None] = mapped_column(Float(), nullable=True)
    dropoff_latitude: Mapped[float | None] = mapped_column(Float(), nullable=True)
    dropoff_longitude: Mapped[float | None] = mapped_column(Float(), nullable=True)
    distance_tenths_km: Mapped[int] = mapped_column(Integer)
    estimated_fare_paise: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(12), default="requested", index=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped[User] = relationship(foreign_keys=[customer_id])
    driver: Mapped[User | None] = relationship(foreign_keys=[driver_id])


class RideRejection(Base):
    __tablename__ = "ride_rejections"
    __table_args__ = (
        UniqueConstraint("ride_id", "driver_id", name="uq_ride_driver_rejection"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ride_id: Mapped[int] = mapped_column(ForeignKey("rides.id", ondelete="CASCADE"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())


class DriverLocation(Base):
    """Latest driver fix only; Phase 3 deliberately stores no location trail."""

    __tablename__ = "driver_locations"
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    latitude: Mapped[float] = mapped_column(Float())
    longitude: Mapped[float] = mapped_column(Float())
    accuracy_m: Mapped[float] = mapped_column(Float())
    captured_at: Mapped[datetime] = mapped_column(DateTime())
    available: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    driver: Mapped[User] = relationship(back_populates="location")


class RideDispatch(Base):
    __tablename__ = "ride_dispatches"
    __table_args__ = (
        UniqueConstraint("ride_id", "driver_id", name="uq_dispatch_ride_driver"),
        CheckConstraint(
            "status IN ('offered','rejected','expired','accepted')",
            name="valid_dispatch_status",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    ride_id: Mapped[int] = mapped_column(ForeignKey("rides.id", ondelete="CASCADE"))
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(10), default="offered", index=True)
    distance_m: Mapped[int] = mapped_column(Integer)
    offered_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(), index=True)


class RideEvent(Base):
    __tablename__ = "ride_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    ride_id: Mapped[int] = mapped_column(
        ForeignKey("rides.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_role: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(60), index=True)
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(), server_default=func.now(), index=True
    )
