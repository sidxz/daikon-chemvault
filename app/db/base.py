from sqlalchemy.orm import declarative_base

# Base class for models
Base = declarative_base()

# Metadata object for handling the database schema
metadata = Base.metadata
