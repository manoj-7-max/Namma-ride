from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import get_engine
from app.routers import admin, auth, events, locations, rides

settings = get_settings()
app = FastAPI(title="Namma Ride API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key"],
)
app.include_router(auth.router)
app.include_router(rides.router)
app.include_router(admin.router)
app.include_router(locations.router)
app.include_router(events.router)


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1 FROM users LIMIT 1"))
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
        "phase": 3,
        "customer_limit": 100,
        "driver_limit": 10,
        "fare_notice": "Demo estimate only; no payment is collected.",
    }
