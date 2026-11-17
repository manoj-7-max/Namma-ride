from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

RideStatus = Literal[
    "requested", "accepted", "arrived", "started", "completed", "cancelled"
]


def normalize_phone(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    if len(digits) != 12 or not digits.startswith("91") or digits[2] not in "6789":
        raise ValueError("Use a valid Indian mobile number")
    return "+" + digits


class OTPRequest(BaseModel):
    phone: str
    role: Literal["customer", "driver"]
    display_name: str | None = Field(default=None, min_length=2, max_length=100)
    vehicle_number: str | None = Field(default=None, min_length=4, max_length=20)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("vehicle_number")
    @classmethod
    def normalize_vehicle(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else value


class OTPVerify(BaseModel):
    challenge_id: int
    phone: str
    otp: str = Field(pattern=r"^\d{6}$")

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        return normalize_phone(value)


class UserOut(BaseModel):
    id: int
    phone: str
    display_name: str
    role: str
    driver_approved: bool
    vehicle_number: str | None
    is_active: bool = True
    driver_suspended: bool = False


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut | None = None


class RideCreate(BaseModel):
    pickup: str = Field(min_length=3, max_length=200)
    dropoff: str = Field(min_length=3, max_length=200)
    estimated_distance_km: float = Field(gt=0, le=100)
    pickup_latitude: float | None = Field(default=None, ge=-90, le=90)
    pickup_longitude: float | None = Field(default=None, ge=-180, le=180)
    dropoff_latitude: float | None = Field(default=None, ge=-90, le=90)
    dropoff_longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("dropoff_longitude")
    @classmethod
    def coordinate_pairs(cls, value: float | None, info):
        fields = info.data
        values = [
            fields.get("pickup_latitude"),
            fields.get("pickup_longitude"),
            fields.get("dropoff_latitude"),
            value,
        ]
        if any(item is not None for item in values) and any(
            item is None for item in values
        ):
            raise ValueError("All pickup and drop-off coordinates are required")
        return value


class DriverLocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(gt=0, le=500)
    captured_at: datetime
    available: bool


class DriverLocationOut(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: float
    captured_at: datetime
    available: bool
    updated_at: datetime


class NearbyDriverSummary(BaseModel):
    available_count: int
    nearest_distance_km: float | None
    radius_km: float


class RideEventOut(BaseModel):
    id: int
    event_type: str
    detail: str | None
    created_at: datetime


class RideStatusUpdate(BaseModel):
    status: RideStatus
    cancellation_reason: str | None = Field(default=None, max_length=200)


class ApprovalUpdate(BaseModel):
    approved: bool


class ActiveUpdate(BaseModel):
    active: bool


class SuspensionUpdate(BaseModel):
    suspended: bool


class CustomerOut(BaseModel):
    id: int
    display_name: str
    phone: str
    active: bool
    created_at: datetime


class DriverOut(BaseModel):
    id: int
    display_name: str
    phone: str
    vehicle_number: str | None
    approved: bool
    suspended: bool = False


class RideOut(BaseModel):
    id: int
    pickup: str
    dropoff: str
    estimated_distance_km: float
    estimated_fare_paise: int
    estimated_fare_rupees: float
    status: str
    customer_id: int
    driver: DriverOut | None
    cancellation_reason: str | None
    created_at: datetime
    pickup_latitude: float | None = None
    pickup_longitude: float | None = None
    dropoff_latitude: float | None = None
    dropoff_longitude: float | None = None
    matching_state: str | None = None
    driver_location: DriverLocationOut | None = None
    driver_eta_minutes: int | None = None
