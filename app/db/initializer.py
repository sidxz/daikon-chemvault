"""Database initialization helpers."""

from sqlalchemy import text

from app.core.logging_config import logger
from app.db.session import engine


async def _enable_postgres_extensions(conn) -> None:
    rdkit_enabled = await conn.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'rdkit'")
    )
    if rdkit_enabled.scalar() is None:
        logger.info("RDKit extension is not active. Activating now.")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"rdkit\";"))
        logger.success("RDKit extension activated.")
    else:
        logger.info("RDKit extension is already active.")

    uuid_enabled = await conn.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp'")
    )
    if uuid_enabled.scalar() is None:
        logger.info("uuid-ossp extension is not active. Activating now.")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
        logger.success("uuid-ossp extension activated.")
    else:
        logger.info("uuid-ossp extension is already active.")


async def initialize_db() -> None:
    """Sets up database extensions when using PostgreSQL."""

    async with engine.begin() as conn:
        try:
            if engine.url.get_backend_name().startswith("postgres"):
                await _enable_postgres_extensions(conn)
            else:
                logger.info(
                    "Skipping PostgreSQL extension checks; non-PostgreSQL backend detected."
                )
            await conn.commit()
        except Exception as exc:  # pragma: no cover - defensive logging
            await conn.rollback()
            logger.error(f"Error initializing database extensions: {exc}")
            raise
