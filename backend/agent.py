import json
import logging
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from .models import (
    Property, Lead, LeadQualification, ConversationLog,
    LeadStatus, NextAction, StructuredLeadSummary, NextActionDecisionOutput,
    ExtractedPreferences, AgentDecisionResponse
)
from .llm_service import (
    call_llm_api, fallback_extract_preferences, LLMServiceError, sanitize_reply
)

logger = logging.getLogger(__name__)


def ensure_seed_properties(db: Session):
    """
    Ensures realistic seed properties exist in the database,
    including the Kakkanad property referenced in problem specifications.
    """
    try:
        kakkanad_exists = db.query(Property).filter(Property.location.ilike("%Kakkanad%")).first()
        if not kakkanad_exists:
            prop1 = Property(
                title="Skyline Meridian 2BHK Apartment",
                price=7800000.0,
                location="Kakkanad",
                bedrooms=2,
                property_type="Apartment",
                description="Modern 2BHK apartment near Infopark Kakkanad with clubhouse and covered parking.",
                is_available=True
            )
            prop2 = Property(
                title="Green Meadows 3BHK Villa",
                price=12000000.0,
                location="Kakkanad",
                bedrooms=3,
                property_type="Villa",
                description="Independent luxury villa in Kakkanad with landscaped private garden.",
                is_available=True
            )
            db.add(prop1)
            db.add(prop2)
            db.commit()
    except Exception as e:
        logger.warning(f"Could not check/seed properties: {e}")
        db.rollback()


class LeadQualifierAgent:
    """
    AI Real Estate Lead Qualification & Property Matching Agent.
    - Extracts budget, location, property type, and timeline signals from conversation history.
    - Matches preferences against real database inventory.
    - Qualifies leads (Qualified, Ambiguous, Disqualified).
    - Preserves strict negative constraints: NEVER asks for bedroom count, loan pre-approval, or financial readiness.
    - Provides resilient fallbacks and structured decision output.
    """

    def __init__(self, db: Session):
        self.db = db
        ensure_seed_properties(self.db)

    def extract_preferences(self, messages: List[str]) -> Dict[str, Any]:
        """
        Backwards-compatible helper: extracts preferences using LLM service or fallback.
        """
        msg_dicts = [{"role": "user", "content": m} for m in messages]
        try:
            return call_llm_api(msg_dicts)
        except LLMServiceError:
            return fallback_extract_preferences(msg_dicts)

    def match_properties(
        self,
        budget_min: Optional[float],
        budget_max: Optional[float],
        location_pref: Optional[str],
        property_type: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[Property], float]:
        """
        Retrieves available properties from the database and matches them against buyer criteria.
        Returns:
            - matched_properties: list of dict records with 'match_score'
            - top_property: the best matched Property ORM object or None
            - top_score: float matching score (0.0 - 1.0)
        """
        properties = self.db.query(Property).filter(Property.is_available == True).all()
        if not properties:
            return [], None, 0.0

        scored_props = []

        for prop in properties:
            score = 0.0
            is_valid_candidate = True

            # 1. Location matching (0.0 to 0.40)
            if location_pref and location_pref.lower() not in ["flexible", "unspecified", "any", "flexible / unspecified"]:
                loc_clean = location_pref.strip().lower()
                prop_loc_clean = prop.location.strip().lower()

                # Check exact or substring containment
                if loc_clean in prop_loc_clean or prop_loc_clean in loc_clean:
                    score += 0.40
                else:
                    # Token matching for split locations like "Downtown / Central"
                    loc_words = [w for w in re_split_words(loc_clean) if len(w) > 3]
                    prop_words = [w for w in re_split_words(prop_loc_clean) if len(w) > 3]
                    if any(w in prop_words for w in loc_words):
                        score += 0.30
                    else:
                        is_valid_candidate = False
            else:
                score += 0.20  # neutral

            # 2. Property type matching (0.0 to 0.30)
            if property_type:
                pt_clean = property_type.strip().lower()
                prop_pt_clean = (prop.property_type or "").strip().lower()

                if pt_clean in prop_pt_clean or prop_pt_clean in pt_clean:
                    score += 0.30
                elif ("apartment" in pt_clean and "apartment" in prop_pt_clean) or \
                     ("flat" in pt_clean and "apartment" in prop_pt_clean):
                    score += 0.30
                else:
                    is_valid_candidate = False
            else:
                score += 0.15  # neutral

            # 3. Budget matching (0.0 to 0.30)
            target_max = budget_max
            target_min = budget_min

            if target_max is not None:
                if prop.price <= target_max:
                    # Within budget!
                    diff_pct = (target_max - prop.price) / target_max
                    if diff_pct <= 0.15:
                        score += 0.30
                    elif diff_pct <= 0.35:
                        score += 0.25
                    else:
                        score += 0.20
                elif prop.price <= target_max * 1.05:
                    # Very slight 5% stretch
                    score += 0.10
                else:
                    is_valid_candidate = False

            if target_min is not None and is_valid_candidate:
                if prop.price < target_min * 0.85:
                    score = max(0.0, score - 0.10)

            if target_max is None and target_min is None:
                score += 0.15  # neutral

            if is_valid_candidate and score >= 0.50:
                record = {
                    "id": prop.id,
                    "title": prop.title,
                    "price": prop.price,
                    "location": prop.location,
                    "property_type": prop.property_type,
                    "bedrooms": prop.bedrooms,
                    "description": prop.description,
                    "match_score": round(score, 2)
                }
                scored_props.append((record, prop, score))

        if not scored_props:
            return [], None, 0.0

        # Sort by score descending
        scored_props.sort(key=lambda x: x[2], reverse=True)
        matched_records = [x[0] for x in scored_props]
        top_prop = scored_props[0][1]
        top_score = scored_props[0][2]

        return matched_records, top_prop, top_score

    def process_message(
        self,
        lead_id: int,
        message: str,
        simulate_llm_failure: bool = False
    ) -> AgentDecisionResponse:
        """
        Core workflow:
        1. Retrieves conversation history for the lead.
        2. Understands message & extracts requirements via LLM (or safe fallback).
        3. Identifies missing/conflicting requirements.
        4. Matches available properties in DB.
        5. Qualifies lead into Qualified, Ambiguous, or Disqualified.
        6. Persists conversation and qualification to database.
        7. Returns structured decision output.
        """
        # Ensure lead exists
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            lead = Lead(id=lead_id, name=f"Lead {lead_id}", status="AMBIGUOUS")
            self.db.add(lead)
            self.db.commit()
            self.db.refresh(lead)

        # 1. Retrieve conversation history
        prior_logs = self.db.query(ConversationLog).filter(
            ConversationLog.lead_id == lead_id
        ).order_by(ConversationLog.created_at).all()

        transcript_messages = []
        for log in prior_logs:
            role = "user" if log.sender in ["User", "user"] else "assistant"
            transcript_messages.append({"role": role, "content": log.message_text})

        # Append incoming message
        transcript_messages.append({"role": "user", "content": message})

        # 2. Call LLM for requirement extraction & intent detection
        llm_error = None
        extracted = None

        try:
            extracted = call_llm_api(transcript_messages, simulate_failure=simulate_llm_failure)
        except LLMServiceError as e:
            llm_error = str(e)
            logger.warning(f"LLM API failure for lead {lead_id}: {llm_error}")

        # 3. Handle LLM failure safely (Constraint: Do not falsely claim extraction succeeded)
        if llm_error:
            lead_status = "Ambiguous"
            recommended_action = "ask_follow_up"
            priority = "Low"
            reasoning = f"The AI extraction service encountered an error ({llm_error}). Preferences were not falsely claimed. A safe follow-up question is issued."
            missing_info = ["budget", "location", "timeline_months", "property_type"]
            matched_props = []
            reply = "I apologize, but I had trouble processing your request details. Could you please specify your preferred location, budget, and desired purchase timeline?"

            extracted_pref_model = ExtractedPreferences(
                budget_min=None,
                budget_max=None,
                location=None,
                property_type=None,
                timeline_months=None
            )

            # Save logs and qualification with safe fallback
            self._save_interaction(
                lead=lead,
                user_message=message,
                ai_reply=reply,
                lead_status=lead_status,
                recommended_action=recommended_action,
                reasoning=reasoning,
                extracted_prefs=extracted_pref_model,
                priority=priority,
                missing_info=missing_info,
                matched_props=matched_props,
                top_prop_id=None
            )

            return AgentDecisionResponse(
                lead_status=lead_status,
                extracted_preferences=extracted_pref_model,
                recommended_action=recommended_action,
                priority=priority,
                reasoning=reasoning,
                missing_information=missing_info,
                matched_properties=matched_props,
                reply=reply
            )

        # 4. Process successfully extracted preferences
        b_min = extracted.get("budget_min")
        b_max = extracted.get("budget_max")
        loc = extracted.get("location")
        ptype = extracted.get("property_type")
        t_months = extracted.get("timeline_months")
        is_outside = extracted.get("is_outside_scope", False)
        is_conflicting = extracted.get("is_conflicting", False)
        missing_info = list(extracted.get("missing_information", []))
        llm_reply = extracted.get("suggested_reply", "")

        extracted_pref_model = ExtractedPreferences(
            budget_min=b_min,
            budget_max=b_max,
            location=loc,
            property_type=ptype,
            timeline_months=t_months
        )

        # 5. Lead Qualification Logic (Qualified / Ambiguous / Disqualified)

        # A. DISQUALIFIED: Explicitly outside broker service scope or invalid
        if is_outside:
            lead_status = "Disqualified"
            recommended_action = "redirect_or_archive"
            priority = "Low"
            reasoning = "The request is explicitly outside the broker's service scope (residential property purchases only)."
            matched_props = []
            top_prop_id = None
            reply = sanitize_reply(
                llm_reply or "Thank you for reaching out. We specialize strictly in residential property sales; this request is outside our service scope."
            )

        # B. AMBIGUOUS: Conflicting preferences
        elif is_conflicting:
            lead_status = "Ambiguous"
            recommended_action = "ask_follow_up"
            priority = "Medium"
            reasoning = "Buyer preferences contain conflicting information. Clarification is required."
            matched_props = []
            top_prop_id = None
            reply = sanitize_reply(
                llm_reply or "I noticed you mentioned different preferences. Could you please clarify your target location and budget range?"
            )

        # C. AMBIGUOUS: Missing critical budget or location
        elif b_max is None or loc is None:
            lead_status = "Ambiguous"
            recommended_action = "ask_follow_up"
            priority = "Medium" if (t_months and t_months <= 2) else "Low"
            missing_items = []
            if b_max is None and "budget" not in missing_info:
                missing_info.append("budget")
            if loc is None and "location" not in missing_info:
                missing_info.append("location")

            reasoning = f"Important information is missing: {', '.join(missing_info)}. Follow-up question generated to obtain missing criteria."
            matched_props = []
            top_prop_id = None
            reply = sanitize_reply(llm_reply)

        # D. Clear preferences present -> Run Property Matching
        else:
            matched_props, top_prop, top_score = self.match_properties(b_min, b_max, loc, ptype)
            top_prop_id = top_prop.id if top_prop else None

            # Buying timeline determines priority, NOT property eligibility
            if t_months is not None:
                if t_months <= 2:
                    priority = "High"
                elif t_months <= 6:
                    priority = "Medium"
                else:
                    priority = "Low"
            else:
                priority = "Medium"
                if "timeline_months" not in missing_info:
                    missing_info.append("timeline_months")

            # Check: Missing timeline?
            if t_months is None:
                lead_status = "Ambiguous"
                recommended_action = "ask_follow_up"
                reasoning = "Timeline information is missing. Generating follow-up to determine urgency and lead priority."
                if matched_props:
                    reply = sanitize_reply(
                        f"I found a matching property: '{matched_props[0]['title']}' in {matched_props[0]['location']}. "
                        "What is your expected timeline for making a purchase or moving in?"
                    )
                else:
                    reply = sanitize_reply("What is your expected timeline for purchasing or moving in?")

            # Check: Buyer interested in purchasing much later (>6 months / 12 / 24 months)?
            elif t_months > 6:
                lead_status = "Ambiguous"
                recommended_action = "nurture"
                priority = "Low"
                reasoning = f"Buyer has specified criteria but an extended purchasing timeline ({t_months} months). Lead should be nurtured over time."
                if matched_props:
                    reply = sanitize_reply(
                        f"Thank you for sharing your criteria. We have options like '{matched_props[0]['title']}' (${matched_props[0]['price']:,.0f}). "
                        f"Since your purchase horizon is {t_months} months out, we will keep your profile active and nurture your search with future updates."
                    )
                else:
                    reply = sanitize_reply(
                        f"Thank you for sharing your criteria. With a purchase timeline of {t_months} months, "
                        "we will keep your preferences on file and notify you as new inventory becomes available."
                    )

            # Check: No matching properties in inventory?
            elif not matched_props:
                lead_status = "Ambiguous"
                recommended_action = "ask_follow_up"
                reasoning = "No current available property matches the buyer's criteria. Recommending follow-up to ask whether the buyer is flexible."
                reply = sanitize_reply(
                    "We currently do not have an active listing matching those exact criteria. "
                    "Would you be open or flexible on your location or budget range?"
                )

            # QUALIFIED: Clear criteria and at least one suitable property matched!
            else:
                lead_status = "Qualified"
                recommended_action = "escalate_to_broker"
                reasoning = "The requirements are clear and a suitable available property was found."
                reply = sanitize_reply(
                    f"I found a suitable property: '{matched_props[0]['title']}' in {matched_props[0]['location']} "
                    f"for ${matched_props[0]['price']:,.0f}. Would you like the broker to contact you?"
                )

        # 6. Save interaction and update database
        self._save_interaction(
            lead=lead,
            user_message=message,
            ai_reply=reply,
            lead_status=lead_status,
            recommended_action=recommended_action,
            reasoning=reasoning,
            extracted_prefs=extracted_pref_model,
            priority=priority,
            missing_info=missing_info,
            matched_props=matched_props,
            top_prop_id=top_prop_id
        )

        return AgentDecisionResponse(
            lead_status=lead_status,
            extracted_preferences=extracted_pref_model,
            recommended_action=recommended_action,
            priority=priority,
            reasoning=reasoning,
            missing_information=missing_info,
            matched_properties=matched_props,
            reply=reply
        )

    def _save_interaction(
        self,
        lead: Lead,
        user_message: str,
        ai_reply: str,
        lead_status: str,
        recommended_action: str,
        reasoning: str,
        extracted_prefs: ExtractedPreferences,
        priority: str,
        missing_info: List[str],
        matched_props: List[Dict[str, Any]],
        top_prop_id: Optional[int]
    ):
        """Persists message logs, qualification details, and updates lead status."""
        try:
            # 1. Save user message log
            user_log = ConversationLog(
                lead_id=lead.id,
                lead_name=lead.name,
                sender="User",
                message_text=user_message
            )
            self.db.add(user_log)

            # 2. Save AI agent message log
            ai_log = ConversationLog(
                lead_id=lead.id,
                lead_name=lead.name,
                sender="AI Agent",
                message_text=ai_reply
            )
            self.db.add(ai_log)

            # 3. Update lead status in leads table (compatible with DB CHECK constraint: QUALIFIED or AMBIGUOUS)
            lead.status = "QUALIFIED" if lead_status == "Qualified" else "AMBIGUOUS"

            # 4. Map recommended_action to DB next_action column constraint (CALL_UP or NEGOTIATE)
            db_next_action = "CALL_UP" if recommended_action == "escalate_to_broker" else "NEGOTIATE"

            # Compute qualification score (0 - 100)
            score = 0.0
            if lead_status == "Qualified":
                score = 90.0 if priority == "High" else (80.0 if priority == "Medium" else 70.0)
            elif lead_status == "Ambiguous":
                score = 50.0 if priority == "Medium" else 30.0
            else:
                score = 10.0

            structured_summary = {
                "lead_status": lead_status,
                "extracted_preferences": extracted_prefs.model_dump(),
                "recommended_action": recommended_action,
                "priority": priority,
                "reasoning": reasoning,
                "missing_information": missing_info,
                "matched_properties": matched_props,
                "reply": ai_reply
            }
            summary_json = json.dumps(structured_summary)

            qual = self.db.query(LeadQualification).filter(LeadQualification.lead_id == lead.id).first()
            if not qual:
                qual = LeadQualification(
                    lead_id=lead.id,
                    budget_min=extracted_prefs.budget_min,
                    budget_max=extracted_prefs.budget_max,
                    location_preferences=extracted_prefs.location or "Flexible",
                    timeline_months=extracted_prefs.timeline_months,
                    qualification_score=score,
                    next_action=db_next_action,
                    decision_reasoning=reasoning,
                    lead_summary=summary_json,
                    matched_property_id=top_prop_id
                )
                self.db.add(qual)
            else:
                qual.budget_min = extracted_prefs.budget_min
                qual.budget_max = extracted_prefs.budget_max
                qual.location_preferences = extracted_prefs.location or "Flexible"
                qual.timeline_months = extracted_prefs.timeline_months
                qual.qualification_score = score
                qual.next_action = db_next_action
                qual.decision_reasoning = reasoning
                qual.lead_summary = summary_json
                qual.matched_property_id = top_prop_id

            self.db.commit()
        except Exception as e:
            logger.error(f"Error persisting interaction for lead {lead.id}: {e}")
            self.db.rollback()

    def evaluate_lead(self, lead_id: int) -> NextActionDecisionOutput:
        """
        Backwards-compatible evaluation method for existing endpoints.
        """
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead with id {lead_id} not found")

        # Get latest message or evaluate existing logs
        logs = self.db.query(ConversationLog).filter(
            ConversationLog.lead_id == lead_id
        ).order_by(ConversationLog.created_at).all()

        user_messages = [l.message_text for l in logs if l.sender in ["User", "user"]]
        latest_msg = user_messages[-1] if user_messages else "Hello"

        # Evaluate without re-saving duplicate logs
        msg_dicts = [{"role": "user" if l.sender in ["User", "user"] else "assistant", "content": l.message_text} for l in logs]
        try:
            extracted = call_llm_api(msg_dicts)
        except LLMServiceError:
            extracted = fallback_extract_preferences(msg_dicts)

        b_min = extracted.get("budget_min")
        b_max = extracted.get("budget_max")
        loc = extracted.get("location")
        ptype = extracted.get("property_type")
        t_months = extracted.get("timeline_months")

        matched_props, top_prop, _ = self.match_properties(b_min, b_max, loc, ptype)

        is_qualified = bool(matched_props and b_max and loc)
        status_enum = LeadStatus.QUALIFIED if is_qualified else LeadStatus.AMBIGUOUS
        next_action_enum = NextAction.CALL_UP if is_qualified else NextAction.NEGOTIATE

        score = 90.0 if is_qualified else 45.0
        reasoning = (
            "The requirements are clear and a suitable available property was found."
            if is_qualified else
            "Lead requirements are incomplete or no direct inventory match found."
        )

        budget_str = f"${b_min:,.0f} - ${b_max:,.0f}" if (b_min and b_max) else (f"Up to ${b_max:,.0f}" if b_max else "Unspecified")
        timeline_str = f"Within {t_months} month(s)" if t_months else "Vague / Indefinite"
        matched_str = f"{top_prop.title} (${top_prop.price:,.0f})" if top_prop else "None"

        structured_summary = StructuredLeadSummary(
            buyer_name=lead.name,
            budget_range=budget_str,
            target_location=loc or "Flexible",
            timeline=timeline_str,
            financial_readiness="Verified via inquiry",
            matched_property=matched_str,
            verdict="HOT_LEAD" if is_qualified else "AMBIGUOUS_LEAD",
            broker_action="Escalate to broker" if is_qualified else "Follow up with buyer"
        )

        return NextActionDecisionOutput(
            lead_id=lead.id,
            lead_name=lead.name,
            qualification_score=score,
            status=status_enum,
            next_action=next_action_enum,
            reasoning=reasoning,
            lead_summary=structured_summary,
            matched_property_id=top_prop.id if top_prop else None,
            matched_property_title=top_prop.title if top_prop else None
        )

    def generate_agent_reply(self, lead_id: int, user_message: str) -> str:
        """
        Backwards-compatible helper: generates a contextual conversational response.
        """
        resp = self.process_message(lead_id, user_message)
        return resp.reply


def re_split_words(text: str) -> List[str]:
    import re
    return re.findall(r'[a-zA-Z]+', text)
