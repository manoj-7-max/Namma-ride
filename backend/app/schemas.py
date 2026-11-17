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


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut | None = None


class RideCreate(BaseModel):
    pickup: str = Field(min_length=3, max_length=200)
    dropoff: str = Field(min_length=3, max_length=200)
    estimated_distance_km: float = Field(gt=0, le=100)


class RideStatusUpdate(BaseModel):
    status: RideStatus
    cancellation_reason: str | None = Field(default=None, max_length=200)


class ApprovalUpdate(BaseModel):
    approved: bool


class DriverOut(BaseModel):
    id: int
    display_name: str
    phone: str
    vehicle_number: str | None
    approved: bool


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
