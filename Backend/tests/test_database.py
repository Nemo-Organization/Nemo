import os
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import create_app
from app.settings import Settings


def database_app(settings: Settings):
    app = create_app(settings)

    @app.get("/test/database")
    def query_database(session: Annotated[Session, Depends(get_session)]):
        return {"value": session.execute(text("SELECT 1")).scalar_one()}

    return app


def test_missing_database_is_an_explicit_service_error():
    app = database_app(Settings(_env_file=None, database_url=None))

    with TestClient(app) as client:
        response = client.get("/test/database")
        assert client.get("/api/v1/health").status_code == 200

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_configured_database_does_not_connect_during_liveness():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:password@127.0.0.1:1/unavailable",
    )

    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to PostgreSQL"
)
def test_session_queries_postgresql_and_closes_after_request():
    settings = Settings(_env_file=None, database_url=os.environ["TEST_DATABASE_URL"])
    app = database_app(settings)

    with TestClient(app) as client:
        assert client.get("/test/database").json() == {"value": 1}
        assert app.state.db_engine.pool.checkedout() == 0


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="Set TEST_DATABASE_URL to PostgreSQL"
)
def test_session_rolls_back_uncommitted_work():
    settings = Settings(_env_file=None, database_url=os.environ["TEST_DATABASE_URL"])
    app = create_app(settings)

    @app.post("/test/uncommitted")
    def uncommitted_write(session: Annotated[Session, Depends(get_session)]):
        session.execute(text("INSERT INTO skeleton_session_probe (id) VALUES (1)"))
        return {"status": "written"}

    with TestClient(app) as client:
        engine = app.state.db_engine
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE skeleton_session_probe (id integer PRIMARY KEY)"))
        try:
            assert client.post("/test/uncommitted").status_code == 200
            with engine.connect() as connection:
                count = connection.execute(text("SELECT count(*) FROM skeleton_session_probe"))
                assert count.scalar_one() == 0
        finally:
            with engine.begin() as connection:
                connection.execute(text("DROP TABLE skeleton_session_probe"))
