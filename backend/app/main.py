import secrets

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import get_engine
from app.models import PilotMember

settings = get_settings()
app = FastAPI(title="Namma Ride API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["X-Admin-Key"],
)
key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def require_admin(key: str | None = Depends(key_header)):
    if not key or not secrets.compare_digest(
        key.encode("utf-8"), settings.admin_api_key.get_secret_value().encode("utf-8")
    ):
        raise HTTPException(401, "Invalid admin key")


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1 FROM pilot_members LIMIT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "Database or migrations unavailable") from None
    return {"status": "ready"}


@app.get("/api/v1/pilot")
def pilot():
    return {
        "name": "Namma Ride",
        "location": "Madurantakam",
        "state": "Tamil Nadu",
        "mode": "private_test",
        "public_ride_operations_enabled": False,
        "payment_processing_enabled": False,
        "bike_taxi_mode": "demo_only",
        "phase": 1,
        "customer_limit": 100,
        "driver_limit": 10,
    }


@app.get("/api/v1/admin/summary", dependencies=[Depends(require_admin)])
def summary():
    try:
        with get_engine().connect() as conn:
            counts = dict(
                conn.execute(
                    select(PilotMember.role, func.count()).group_by(PilotMember.role)
                ).all()
            )
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable") from None
    return {
        "customers": counts.get("customer", 0),
        "drivers": counts.get("driver", 0),
        "customer_limit": 100,
        "driver_limit": 10,
    }
