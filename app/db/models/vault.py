# from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, JSON, Enum
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.orm import relationship
# import uuid
# import datetime

# class Vault(Base):
#     __tablename__ = "vaults"

#     # Unique identifier for each vault
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True, unique=True, nullable=False)
    
#     # Name and description
#     name = Column(String, index=True, nullable=False)
#     description = Column(String, nullable=True)
    
#     # Ownership and collaboration
#     owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)  # Foreign key to users table
#     shared_with = Column(JSON, nullable=True)  # List of users or groups that can access this vault
#     visibility = Column(Enum('public', 'private', name='visibility_enum'), default='private', nullable=False)

#     # Project information
#     project_type = Column(String, nullable=True)  # e.g., lead optimization, hit discovery
#     external_reference_id = Column(String, nullable=True)  # Reference to external system

#     # Collaboration details
#     collaborators = Column(JSON, nullable=True)  # JSON list of collaborators
    
#     # Access control and status
#     access_control = Column(Enum('read-only', 'write', 'admin', name='access_control_enum'), default='read-only', nullable=False)
#     status = Column(Enum('active', 'archived', 'locked', name='status_enum'), default='active', nullable=False)
    
#     # Other metadata
   
#     data_source = Column(String, nullable=True)  # Where the data comes from (in-house, external, etc.)
#     compound_count = Column(Integer, default=0, nullable=False)  # Number of molecules in the vault
    
#     # Relationship to Molecule table
#     molecules = relationship("Molecule", back_populates="vault")
