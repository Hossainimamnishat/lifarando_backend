from __future__ import annotations
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from alembic import context

# Alembic Config
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Project imports (alembic.ini must have: prepend_sys_path = .)
from app.config import settings  # loads .env
from app.db.base import Base
from app.models import user, restaurant, menu, order, driver, payment, geo  # noqa: F401

target_metadata = Base.metadata

# Allow CLI override: alembic -x db_url=postgresql+asyncpg://...
cmd_opts = context.get_x_argument(as_dictionary=True)
override_url = cmd_opts.get("db_url")

db_url = override_url or settings.DATABASE_URL
if not db_url or not isinstance(db_url, str):
    raise RuntimeError(
        "DATABASE_URL is empty. Set it in .env (or pass -x db_url=...). "
        "Example: postgresql+asyncpg://postgres:postgres@localhost:5432/food"
    )

# Inject URL at runtime
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=False,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode' with async engine."""
    connectable: AsyncEngine = create_async_engine(
        db_url,
        poolclass=pool.NullPool,
        future=True,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
