from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create an async engine for SQLAlchemy
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Create a session factory bound to the engine
AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


async def initialize_db():
    """
    Sets up the database by creating necessary extensions and tables if they don't exist.

    Args:
        None

    Returns:
        None
    """
    async with engine.begin() as conn:
        try:
            # Enable RDKit extension if not already enabled
            await conn.execute(
                """
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'rdkit') THEN
                        CREATE EXTENSION "rdkit";
                    END IF;
                END $$;
                """
            )
            # Enable uuid-ossp extension if not already enabled
            await conn.execute(
                """
                DO $$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp') THEN
                        CREATE EXTENSION "uuid-ossp";
                    END IF;
                END $$;
                """
            )
            await conn.commit()
        except Exception as e:
            await conn.rollback()
            raise e
