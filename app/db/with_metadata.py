from sqlalchemy import Column, DateTime, String, Boolean, Integer, Float, UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr
import datetime

@as_declarative()
class WithMetadata:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    # Timestamps
    _created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    _updated_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    _deleted_at = Column(DateTime, nullable=True)

    # Audit information
    _created_by = Column(UUID(as_uuid=True), nullable=True)
    _updated_by = Column(UUID(as_uuid=True), nullable=True)
    _deleted_by = Column(UUID(as_uuid=True), nullable=True)

    # Soft delete
    _is_deleted = Column(Boolean, default=False)

    # Status and versioning
    _status = Column(String, default="active")
    _version = Column(Integer, default=1)

    # Ownership/tenant
    _owner_id = Column(UUID(as_uuid=True), nullable=True)
    _tenant_id = Column(UUID(as_uuid=True), nullable=True)

    # Tags
    _tags = Column(String, nullable=True)
