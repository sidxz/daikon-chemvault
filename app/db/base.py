from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Ensure the DATABASE_URL is for async usage (e.g., 'postgresql+asyncpg://user:password@localhost/dbname')
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create the async engine with appropriate options
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,  # Enable SQL query logging, useful for debugging, disable in production for better performance
    future=True,  # Use the 2.0 API, ensures compatibility with SQLAlchemy 2.0 features
    pool_size=10,  # Initial connection pool size, adjust based on your application's concurrency requirements
    max_overflow=20,  # Allow additional connections beyond the pool_size in high-demand scenarios
)

# Async sessionmaker factory
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,  # Explicit control over transactions, typically False in modern applications
    autoflush=False,  # Prevent automatic flushing to the database, manually flush when needed
    expire_on_commit=False,  # Prevent attributes from being expired after commit, allows continued access to the data
)

# Base class for models
Base = declarative_base()

# Metadata object for handling the database schema
metadata = Base.metadata
