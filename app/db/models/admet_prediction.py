from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.with_metadata import WithMetadata
from app.db.base import Base


class AdmetPrediction(Base, WithMetadata):
    """
    SQLAlchemy model for storing ADMET predictions from admet_ai.
    """
    __tablename__ = "admet_predictions"

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("molecules.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    predictions = Column(JSONB, nullable=True)
    model_version = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    error = Column(String, nullable=True)

    molecule = relationship("Molecule", back_populates="admet_prediction")
