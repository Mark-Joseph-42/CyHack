from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import engine, get_db, Base
from .models import (
    Property, Lead, LeadQualification, ConversationLog,
    LeadStatus, NextAction, SenderType,
    PropertyResponse, PropertyCreate,
    LeadResponse, LeadCreate,
    ConversationLogResponse, ConversationLogCreate,
    LeadQualificationResponse, NextActionDecisionOutput,
    LeadChatRequest, LeadChatResponse,
    AgentDecisionResponse, IncomingMessageRequest
)
from .agent import LeadQualifierAgent

# Initialize DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Real Estate Lead Qualifier AI Agent API",
    description="Problem #4: Intelligent Lead Engagement, Inventory Matching, and Next-Action Decision Engine",
    version="1.0.0"
)

# Enable CORS for frontend or local integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Real Estate Lead Qualifier API is running",
        "problem_statement": "Problem #4: Real Estate Lead Qualifier",
        "docs_url": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# =====================================================================
# PROPERTY ENDPOINTS
# =====================================================================
@app.get("/api/properties", response_model=List[PropertyResponse])
def get_properties(
    location: Optional[str] = Query(None, description="Filter by location keyword"),
    max_price: Optional[float] = Query(None, description="Filter by maximum price"),
    db: Session = Depends(get_db)
):
    query = db.query(Property).filter(Property.is_available == True)
    if location:
        query = query.filter(Property.location.ilike(f"%{location}%"))
    if max_price:
        query = query.filter(Property.price <= max_price)
    return query.all()


@app.post("/api/properties", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create_property(prop_in: PropertyCreate, db: Session = Depends(get_db)):
    prop = Property(**prop_in.model_dump())
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


# =====================================================================
# LEAD ENDPOINTS
# =====================================================================
@app.get("/api/leads", response_model=List[LeadResponse])
def get_leads(
    status_filter: Optional[LeadStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db)
):
    query = db.query(Lead)
    if status_filter:
        query = query.filter(Lead.status == status_filter.value)
    return query.all()


@app.post("/api/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(lead_in: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(
        name=lead_in.name,
        email=lead_in.email,
        phone=lead_in.phone,
        status=lead_in.status.value if lead_in.status else LeadStatus.AMBIGUOUS.value
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # If an initial inquiry message was provided, process and qualify
    if lead_in.initial_message:
        agent = LeadQualifierAgent(db)
        agent.process_message(lead.id, lead_in.initial_message)
        db.refresh(lead)

    return lead


@app.get("/api/leads/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


# =====================================================================
# AGENT INTERACTIVE CHAT & MESSAGE ENDPOINTS
# =====================================================================
@app.post("/api/leads/{lead_id}/chat", response_model=LeadChatResponse)
def chat_with_agent(
    lead_id: int,
    chat_req: LeadChatRequest,
    simulate_llm_failure: bool = Query(False, description="Simulate LLM API failure for testing"),
    db: Session = Depends(get_db)
):
    """
    Existing endpoint: engages agent for specific lead_id.
    Maintains history, evaluates qualifications, matches properties, and returns decision.
    """
    agent = LeadQualifierAgent(db)
    result = agent.process_message(
        lead_id=lead_id,
        message=chat_req.message,
        simulate_llm_failure=simulate_llm_failure
    )
    return LeadChatResponse(
        lead_status=result.lead_status,
        extracted_preferences=result.extracted_preferences,
        recommended_action=result.recommended_action,
        priority=result.priority,
        reasoning=result.reasoning,
        missing_information=result.missing_information,
        matched_properties=result.matched_properties,
        reply=result.reply,
        qualification_evaluated=True
    )


@app.post("/api/message", response_model=AgentDecisionResponse)
@app.post("/api/chat", response_model=AgentDecisionResponse)
def handle_incoming_message(
    incoming: IncomingMessageRequest,
    simulate_llm_failure: bool = Query(False, description="Simulate LLM API failure for testing"),
    db: Session = Depends(get_db)
):
    """
    Standard message endpoint for buyer React frontend:
    {
      "lead_id": 501,
      "message": "I need an apartment in Kakkanad for around 80 lakh, within two months."
    }
    Retrieves conversation history, processes message with LLM, matches real properties,
    saves state, and returns full structured decision output.
    """
    agent = LeadQualifierAgent(db)
    result = agent.process_message(
        lead_id=incoming.lead_id,
        message=incoming.message,
        simulate_llm_failure=simulate_llm_failure
    )
    return result


# =====================================================================
# QUALIFIER AGENT EVALUATION & DECISION ENDPOINT
# (Satisfies: Next-Action Decision with reasoning + Structured Lead Summary)
# =====================================================================
@app.post("/api/leads/{lead_id}/qualify", response_model=NextActionDecisionOutput)
def qualify_lead(lead_id: int, db: Session = Depends(get_db)):
    """
    Triggers the Real Estate Qualifier Agent:
    - Analyzes conversation history for budget, location, timeline
    - Matches against available inventory
    - Computes qualification score
    - Determines Next-Action Decision (CALL_UP, NEGOTIATE, FOLLOW_UP, DISCARD) with reasoning
    - Returns structured lead summary for broker
    """
    agent = LeadQualifierAgent(db)
    try:
        decision = agent.evaluate_lead(lead_id)
        return decision
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/qualifications", response_model=List[LeadQualificationResponse])
def get_all_qualifications(
    action_filter: Optional[NextAction] = Query(None, alias="action"),
    db: Session = Depends(get_db)
):
    query = db.query(LeadQualification)
    if action_filter:
        query = query.filter(LeadQualification.next_action == action_filter.value)
    return query.all()
