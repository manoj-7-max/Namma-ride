from functools import lru_cache

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.config import get_settings


@lru_cache
def get_engine():
    s = get_settings()
    return create_engine(
        URL.create(
            "postgresql+psycopg",
            username=s.db_user,
            password=s.db_password.get_secret_value(),
            host=s.db_host,
            port=s.db_port,
            database=s.db_name,
        ),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def get_db():
    with Session(get_engine()) as session:
        yield session
