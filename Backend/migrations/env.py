from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

import app.models  # noqa: F401  Registers every table on Base.metadata.
from app.db import Base, create_database_engine
from app.settings import Settings

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _explicit_url() -> str | None:
    """Return a URL passed with `-x url=...` or set on the Alembic config, if any."""
    return context.get_x_argument(as_dictionary=True).get("url") or config.get_main_option(
        "sqlalchemy.url"
    )


def run_migrations_offline() -> None:
    url = _explicit_url()
    if url is None:
        settings = Settings()
        if settings.database_url is None:
            raise RuntimeError("DATABASE_URL is required to run migrations.")
        url = settings.database_url.get_secret_value()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_with_connection(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Tests pass an open connection so a test run can never fall back to .env DATABASE_URL.
    connection = config.attributes.get("connection")
    if connection is not None:
        _run_with_connection(connection)
        return

    url = _explicit_url()
    engine = (
        create_engine(url, hide_parameters=True)
        if url is not None
        else create_database_engine(Settings())
    )
    try:
        with engine.connect() as connection:
            _run_with_connection(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
