from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.errors import ApplicationError
from app.settings import Settings


class Base(DeclarativeBase):
    """Shared metadata for the domain models added in the database milestone."""


def create_database_engine(settings: Settings) -> Engine:
    if settings.database_url is None:
        raise RuntimeError("DATABASE_URL is required for database operations.")
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        connect_args={"connect_timeout": 5},
        hide_parameters=True,
    )


def get_session(request: Request) -> Iterator[Session]:
    engine = request.app.state.db_engine
    if engine is None:
        raise ApplicationError(503, "SERVICE_UNAVAILABLE", "Database is not configured.")
    with Session(engine) as session:
        yield session
