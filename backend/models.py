import enum
from datetime import datetime
from typing import List, Optional, Union
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, ConfigDict

from .database import Base


# =====================================================================
# ENUMS
# =====================================================================
class LeadStatus(str, enum.Enum):
    QUALIFIED = "QUALIFIED"
    AMBIGUOUS = "AMBIGUOUS"


class NextAction(str, enum.Enum):
    CALL_UP = "CALL_UP"
    NEGOTIATE = "NEGOTIATE"


class SenderType(str, enum.Enum):
    USER = "User"
    AI_AGENT = "AI Agent"


# =====================================================================
# SQLALCHEMY ORM MODELS
# =====================================================================
class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    price = Column(Float, nullable=False, index=True)
    location = Column(String(255), nullable=False, index=True)
    bedrooms = Column(Integer, default=2)
    property_type = Column(String(100), default="Apartment")
    description = Column(Text, nullable=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to qualifications
    qualifications = relationship("LeadQualification", back_populates="matched_property")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    status = Column(
        String(50),
        default=LeadStatus.AMBIGUOUS.value,
        nullable=False,
        index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    qualification = relationship("LeadQualification", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    conversation_logs = relationship("ConversationLog", back_populates="lead", cascade="all, delete-orphan", order_by="ConversationLog.created_at")


class LeadQualification(Base):
    __tablename__ = "lead_qualifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    location_preferences = Column(Text, nullable=True)
    timeline_months = Column(Integer, nullable=True)
    qualification_score = Column(Float, default=0.0)
    next_action = Column(String(50), nullable=False, index=True)  # CALL_UP, NEGOTIATE, etc.
    decision_reasoning = Column(Text, nullable=False)
    lead_summary = Column(Text, nullable=False)
    matched_property_id = Column(Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", back_populates="qualification")
    matched_property = relationship("Property", back_populates="qualifications")


class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_name = Column(String(255), nullable=False)
    sender = Column(String(50), nullable=False)  # 'User' or 'AI Agent'
    message_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    lead = relationship("Lead", back_populates="conversation_logs")


# =====================================================================
# PYDANTIC SCHEMAS (API & AGENT CONTRACTS)
# =====================================================================

# Property schemas
class PropertyBase(BaseModel):
    title: str
    price: float
    location: str
    bedrooms: Optional[int] = 2
    property_type: Optional[str] = "Apartment"
    description: Optional[str] = None
    is_available: Optional[bool] = True


class PropertyCreate(PropertyBase):
    pass


class PropertyResponse(PropertyBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Conversation schemas
class ConversationLogCreate(BaseModel):
    lead_id: int
    lead_name: str
    sender: SenderType
    message_text: str


class ConversationLogResponse(BaseModel):
    id: int
    lead_id: int
    lead_name: str
    sender: str
    message_text: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Structured Lead Summary schema (Expected Output Requirement)
class StructuredLeadSummary(BaseModel):
    buyer_name: str
    budget_range: str
    target_location: str
    timeline: str
    financial_readiness: str
    matched_property: Optional[str] = None
    verdict: str = Field(description="E.g. HOT_LEAD, QUALIFIED_NEGOTIATION, AMBIGUOUS_UNQUALIFIED")
    broker_action: str = Field(description="Clear directive for the broker")


# Agent Qualification & Decision Output schema
class NextActionDecisionOutput(BaseModel):
    lead_id: int
    lead_name: str
    qualification_score: float = Field(ge=0.0, le=100.0, description="Lead readiness score (0-100)")
    status: LeadStatus
    next_action: NextAction
    reasoning: str = Field(description="Explanatory reasoning behind the next action decision")
    lead_summary: Union[StructuredLeadSummary, str]
    matched_property_id: Optional[int] = None
    matched_property_title: Optional[str] = None


# Lead Qualification DB schemas
class LeadQualificationCreate(BaseModel):
    lead_id: int
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    location_preferences: Optional[str] = None
    timeline_months: Optional[int] = None
    qualification_score: float = 0.0
    next_action: NextAction
    decision_reasoning: str
    lead_summary: str
    matched_property_id: Optional[int] = None


class LeadQualificationResponse(BaseModel):
    id: int
    lead_id: int
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    location_preferences: Optional[str] = None
    timeline_months: Optional[int] = None
    qualification_score: float
    next_action: str
    decision_reasoning: str
    lead_summary: str
    matched_property_id: Optional[int] = None
    matched_property: Optional[PropertyResponse] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Lead schemas
class LeadBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[LeadStatus] = LeadStatus.AMBIGUOUS


class LeadCreate(LeadBase):
    initial_message: Optional[str] = None


class LeadResponse(LeadBase):
    id: int
    status: str
    created_at: Optional[datetime] = None
    qualification: Optional[LeadQualificationResponse] = None
    conversation_logs: Optional[List[ConversationLogResponse]] = []

    model_config = ConfigDict(from_attributes=True)


# Chat request/response for Interactive Agent engagement
class LeadChatRequest(BaseModel):
    message: str


class LeadChatResponse(BaseModel):
    reply: str
    qualification_evaluated: bool = False
    decision: Optional[NextActionDecisionOutput] = None
