from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config, AsyncConnection

from alembic import context

from app.db.base import Base
from app.db.models.molecule import Molecule
from app.db.models.raw_molecule import RawMolecule
from app.db.models.parent_molecule import ParentMolecule

import os

from dotenv import load_dotenv
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Read the DATABASE_URL environment variable and set it in the config
database_url = os.getenv('DATABASE_URL')
if database_url is None:
    raise ValueError("DATABASE_URL environment variable not set")
config.set_main_option('sqlalchemy.url', database_url)

print(f"DATABASE_URL: {database_url}")

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: AsyncConnection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an AsyncEngine
    and associate a connection with the context.

    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())
