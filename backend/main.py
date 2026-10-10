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
    LeadChatRequest, LeadChatResponse
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


import os
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

# Setup frontend static directory
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


@app.get("/")
def root():
    """Redirects root directly to the Buyer Discovery frontend."""
    return RedirectResponse(url="/app/buyer.html")



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

    # If an initial inquiry message was provided, log it and generate agent greeting
    if lead_in.initial_message:
        user_log = ConversationLog(
            lead_id=lead.id,
            lead_name=lead.name,
            sender=SenderType.USER.value,
            message_text=lead_in.initial_message
        )
        db.add(user_log)

        agent = LeadQualifierAgent(db)
        ai_reply = agent.generate_agent_reply(lead.id, lead_in.initial_message)
        ai_log = ConversationLog(
            lead_id=lead.id,
            lead_name=lead.name,
            sender=SenderType.AI_AGENT.value,
            message_text=ai_reply
        )
        db.add(ai_log)
        db.commit()
        db.refresh(lead)

    return lead


@app.get("/api/leads/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


# =====================================================================
# AGENT INTERACTIVE CHAT ENDPOINT
# =====================================================================
@app.post("/api/leads/{lead_id}/chat", response_model=LeadChatResponse)
def chat_with_agent(
    lead_id: int,
    chat_req: LeadChatRequest,
    auto_qualify: bool = Query(True, description="Automatically re-evaluate qualification after message"),
    db: Session = Depends(get_db)
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # 1. Record incoming user message
    user_log = ConversationLog(
        lead_id=lead.id,
        lead_name=lead.name,
        sender=SenderType.USER.value,
        message_text=chat_req.message
    )
    db.add(user_log)
    db.commit()

    # 2. Agent generates response
    agent = LeadQualifierAgent(db)
    agent_reply = agent.generate_agent_reply(lead.id, chat_req.message)

    # 3. Record agent response
    ai_log = ConversationLog(
        lead_id=lead.id,
        lead_name=lead.name,
        sender=SenderType.AI_AGENT.value,
        message_text=agent_reply
    )
    db.add(ai_log)
    db.commit()

    decision = None
    if auto_qualify:
        decision = agent.evaluate_lead(lead.id)

    return LeadChatResponse(
        reply=agent_reply,
        qualification_evaluated=auto_qualify,
        decision=decision
    )


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
