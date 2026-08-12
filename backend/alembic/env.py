from __future__ import annotations

from logging.config import fileConfig

import app.models  # noqa: F401
from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    return get_settings().database_url


def mask_database_url(url: str) -> str:
    return str(make_url(url).render_as_string(hide_password=True))


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        connection_context = connectable.connect()
    except OperationalError as exc:
        masked_url = mask_database_url(configuration["sqlalchemy.url"])
        raise RuntimeError(
            "Alembic could not connect to PostgreSQL. "
            f"Current URL: {masked_url}. "
            "Check DATABASE_URL in .env, make sure the database exists, "
            "or start the bundled local database with: docker compose up -d db"
        ) from exc

    with connection_context as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
