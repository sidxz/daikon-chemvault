from sqlalchemy import Column, ForeignKey, Boolean, String
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.db.with_metadata import WithMetadata
from app.db.base import Base


class Pains(Base, WithMetadata):
    """
    SQLAlchemy model for storing PAINS detection results.
    """
    __tablename__ = "pains"

    id = Column(UUID(as_uuid=True), ForeignKey("molecules.id", ondelete="CASCADE"), primary_key=True, index=True)
    rdkit_pains = Column(Boolean, nullable=False, default=False)
    rdkit_pains_label = Column(ARRAY(String), nullable=True)

    # Define relationship with Molecule model
    molecule = relationship("Molecule", back_populates="pains")
