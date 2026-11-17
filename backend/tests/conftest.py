import os

os.environ.setdefault("DB_PASSWORD", "test-database-password-only")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-for-private-pilot-only")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-private-pilot-only")
os.environ.setdefault("OTP_PEPPER", "test-otp-pepper-for-private-pilot-only")
os.environ.setdefault("EXPOSE_TEST_OTP", "false")
os.environ.setdefault(
    "PILOT_OTP_ADMIN_API_KEY", "test-pilot-otp-admin-key-private-only"
)
os.environ.setdefault(
    "PILOT_OTP_ENCRYPTION_KEY", "vqpmAs4Ia5oeruKt4H384Mu8lxvy1inTjGu5w2CvhLw="
)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def override_db():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_db] = override_db


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
