from sqlalchemy import text  # Import the text function
from app.db.base import engine  # Import the existing engine from base.py
from app.core.logging_config import logger  # Import the configured logger


async def initialize_db():
    """
    Sets up the database by creating necessary extensions and tables if they don't exist.

    Returns:
        None
    """
    async with engine.begin() as conn:
        try:
            # Check if the RDKit extension is already active
            result = await conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'rdkit'")
            )
            rdkit_extension_active = result.scalar() is not None

            if rdkit_extension_active:
                logger.info("RDKit extension is already active.")
            else:
                logger.info("RDKit extension is not active. Activating now.")
                await conn.execute(
                    text(
                        """
                        CREATE EXTENSION IF NOT EXISTS "rdkit";
                        """
                    )
                )
                logger.success("RDKit extension activated.")

            # Check if the uuid-ossp extension is already active
            result = await conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp'")
            )
            uuid_ossp_extension_active = result.scalar() is not None

            if uuid_ossp_extension_active:
                logger.info("uuid-ossp extension is already active.")
            else:
                logger.info("uuid-ossp extension is not active. Activating now.")
                await conn.execute(
                    text(
                        """
                        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
                        """
                    )
                )
                logger.success("uuid-ossp extension activated.")

            # Commit the changes
            await conn.commit()
        except Exception as e:
            # Rollback the transaction if there is an error
            await conn.rollback()
            logger.error(f"Error initializing database extensions: {e}")
            raise e  # Re-raise the exception to handle it in the calling code
