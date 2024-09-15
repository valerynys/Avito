import enum
import uuid
from sqlalchemy import Column, String, Text, Enum, ForeignKey, TIMESTAMP, func, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class OrganizationType(enum.Enum):
    IE = 'IE'
    LLC = 'LLC'
    JSC = 'JSC'


class BidStatus(enum.Enum):
    CREATED = "Created"
    PUBLISHED = "Published"
    CANCELED = "Canceled"


class BidDecision(enum.Enum):
    APPROVED = "Approved"
    REJECTED = "Rejected"


class AuthorType(enum.Enum):
    ORGANIZATION = "Organization"
    USER = "User"


class Employee(Base):
    __tablename__ = 'employee'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    tenders = relationship("Tender", back_populates="creator")
    responsibles = relationship("OrganizationResponsible", back_populates="user")


class Organization(Base):
    __tablename__ = 'organization'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    type = Column(Enum(OrganizationType, name="organization_type"))
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    responsibilities = relationship("OrganizationResponsible", back_populates="organization")


class OrganizationResponsible(Base):
    __tablename__ = 'organization_responsible'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organization.id', ondelete='CASCADE'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('employee.id', ondelete='CASCADE'))

    organization = relationship('Organization', back_populates='responsibilities')
    user = relationship('Employee', back_populates='responsibles')


class Tender(Base):
    __tablename__ = 'tender'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    status = Column(Enum('Created', 'Published', 'Closed', name='status_enum'), nullable=False)
    service_type = Column(Enum('Construction', 'Delivery', 'Manufacture', name='service_type_enum'), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organization.id'), nullable=False)
    creator_username = Column(String(50), ForeignKey('employee.username'), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    creator = relationship("Employee", back_populates="tenders")
    bid = relationship("Bid", back_populates="tender")
    versions = relationship("TenderVersion", back_populates="tender")


class TenderVersion(Base):
    __tablename__ = 'tender_version'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey('tender.id', ondelete='CASCADE'))
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    status = Column(Enum('Created', 'Published', 'Closed', name='status_enum'), nullable=False)
    service_type = Column(Enum('Construction', 'Delivery', 'Manufacture', name='service_type_enum'), nullable=False)
    version = Column(Integer, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organization.id'), nullable=False)
    creator_username = Column(String(50), ForeignKey('employee.username'), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())

    tender = relationship("Tender", back_populates="versions")

class Bid(Base):
    __tablename__ = 'bid'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    status = Column(Enum('Created', 'Published', 'Canceled', name='bid_status_enum'), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    tender_id = Column(UUID(as_uuid=True), ForeignKey('tender.id', ondelete='CASCADE'), nullable=False)
    author_type = Column(Enum('Organization', 'User', name='author_type_enum'), nullable=False)
    author_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    tender = relationship("Tender", back_populates="bid")
    decisions = relationship("BidDecisionLog", back_populates="bid")
    feedback = relationship("BidFeedback", back_populates="bid")
    versions = relationship("BidVersion", back_populates="bid")

class BidDecisionLog(Base):
    __tablename__ = 'bid_decision_log'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bid_id = Column(UUID(as_uuid=True), ForeignKey('bid.id', ondelete='CASCADE'), nullable=False)
    responsible_id = Column(UUID(as_uuid=True), ForeignKey('organization_responsible.id', ondelete='CASCADE'), nullable=False)
    decision = Column(Enum('Approved', 'Rejected', name='decision_type_enum'), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    bid = relationship("Bid", back_populates="decisions")
    responsible = relationship("OrganizationResponsible")

class BidFeedback(Base):
    __tablename__ = 'bid_feedback'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bid_id = Column(UUID(as_uuid=True), ForeignKey('bid.id', ondelete='CASCADE'), nullable=False)
    responsible_id = Column(UUID(as_uuid=True), ForeignKey('organization_responsible.id', ondelete='CASCADE'), nullable=False)
    description = Column(String(1000), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    bid = relationship("Bid", back_populates="feedback")
    responsible = relationship("OrganizationResponsible")

class BidVersion(Base):
    __tablename__ = 'bid_version'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bid_id = Column(UUID(as_uuid=True), ForeignKey('bid.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    status = Column(Enum("Created", "Published", "Canceled", name='bid_status_enum'), nullable=False)
    version = Column(Integer, nullable=False)
    tender_id = Column(UUID(as_uuid=True), ForeignKey('tender.id'), nullable=False)
    author_type = Column(Enum('Organization', 'User', name='author_type_enum'), nullable=False)
    author_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())

    bid = relationship("Bid", back_populates="versions")
    tender = relationship("Tender")