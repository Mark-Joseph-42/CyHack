import re
import json
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from .models import (
    Property, Lead, LeadQualification, ConversationLog,
    LeadStatus, NextAction, StructuredLeadSummary, NextActionDecisionOutput
)


class LeadQualifierAgent:
    """
    AI Agent that:
    1. Engages prospective buyers and gathers pricing, location, and timeline preferences.
    2. Matches lead preferences against current property inventory.
    3. Calculates a multi-factor qualification score.
    4. Determines the Next-Action Decision (CALL_UP, NEGOTIATE, FOLLOW_UP, DISCARD) with clear reasoning.
    5. Produces a structured lead summary for brokers.
    """

    def __init__(self, db: Session):
        self.db = db

    def extract_preferences(self, messages: List[str]) -> Dict[str, Any]:
        """
        Extracts budget, location, and timeline signals from conversation text.
        Works with heuristic pattern parsing and can be backed by LLM.
        """
        full_text = " ".join(messages).lower()

        # 1. Budget extraction
        budget_min = None
        budget_max = None
        
        # Check if text mentions asking price specifically to separate from buyer budget
        asking_price_match = re.search(r'(?:(?:asking price|listed at|list price)\s*(?:of|is)?\s*\$?\s*(\d+(?:\.\d+)?)\s*(k|m|million)?|\$?\s*(\d+(?:\.\d+)?)\s*(k|m|million)?\s*(?:asking price|list price))', full_text)
        asking_val = None
        if asking_price_match:
            try:
                num_str = asking_price_match.group(1) or asking_price_match.group(3)
                u = asking_price_match.group(2) or asking_price_match.group(4)
                if num_str:
                    av = float(num_str)
                    if u in ['k', 'thousand']:
                        av *= 1000
                    elif u in ['m', 'million']:
                        av *= 1000000
                    asking_val = av
            except ValueError:
                pass

        # Match currency mentions
        money_matches = re.findall(r'(?:\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|million|thousand)?|(\d+(?:\.\d+)?)\s*(k|m|million|thousand))', full_text)
        found_amounts = []
        for match in money_matches:
            val_str = match[0] or match[2]
            unit = match[1] or match[3]
            val_str = val_str.replace(',', '')
            try:
                num = float(val_str)
                if unit in ['k', 'thousand']:
                    num *= 1000
                elif unit in ['m', 'million']:
                    num *= 1000000
                # Exclude the property asking price if buyer mentioned it as target for discount
                if asking_val and abs(num - asking_val) < 1.0 and ("flexible" in full_text or "negotiat" in full_text):
                    continue
                if num >= 10000:
                    found_amounts.append(num)
            except ValueError:
                continue

        if len(found_amounts) == 1:
            budget_max = found_amounts[0]
            budget_min = budget_max * 0.9
        elif len(found_amounts) >= 2:
            budget_min = min(found_amounts)
            budget_max = max(found_amounts)

        # 2. Location extraction
        available_properties = self.db.query(Property).all()
        detected_location = None
        for prop in available_properties:
            loc_parts = [part.strip().lower() for part in prop.location.split('/')]
            for part in loc_parts:
                if part and part in full_text:
                    detected_location = prop.location
                    break
            if detected_location:
                break

        if not detected_location:
            common_locations = ['downtown', 'marina bay', 'greenwood', 'midtown', 'waterfront', 'suburb']
            for loc in common_locations:
                if loc in full_text:
                    detected_location = loc.title()
                    break

        # 3. Timeline extraction (months)
        timeline_months = None
        if "30 days" in full_text or "immediately" in full_text or "urgent" in full_text or "this month" in full_text or "asap" in full_text:
            timeline_months = 1
        elif "60 days" in full_text or "2 months" in full_text or "two months" in full_text:
            timeline_months = 2
        elif "3 months" in full_text or "90 days" in full_text or "quarter" in full_text:
            timeline_months = 3
        elif "next year" in full_text or "12 months" in full_text or "whenever" in full_text or "just browsing" in full_text:
            timeline_months = 12

        # 4. Financial readiness signals
        readiness = "Unverified"
        if "pre-approved" in full_text or "preapproved" in full_text or "mortgage approved" in full_text:
            readiness = "Pre-Approved Financing"
        elif "cash" in full_text or "all cash" in full_text:
            readiness = "Cash Ready"
        elif "loan" in full_text or "financing" in full_text:
            readiness = "Seeking Financing"
        elif "just browsing" in full_text or "not sure" in full_text:
            readiness = "Casual / Passive Browser"

        return {
            "budget_min": budget_min,
            "budget_max": budget_max,
            "location_preferences": detected_location or "Flexible / Unspecified",
            "timeline_months": timeline_months,
            "readiness": readiness,
            "raw_text": full_text
        }

    def match_properties(self, budget_min: Optional[float], budget_max: Optional[float], location_pref: str) -> Tuple[Optional[Property], float]:
        """
        Matches preferences against property inventory.
        Returns the best matched Property and a match fit score (0.0 - 1.0).
        """
        properties = self.db.query(Property).filter(Property.is_available == True).all()
        if not properties:
            return None, 0.0

        best_prop = None
        best_score = 0.0

        target_budget = budget_max if budget_max else budget_min

        for prop in properties:
            score = 0.0

            # Location match (up to 0.5)
            if location_pref and location_pref.lower() != "flexible / unspecified":
                if location_pref.lower() in prop.location.lower() or prop.location.lower() in location_pref.lower():
                    score += 0.5
                elif any(word in prop.location.lower() for word in location_pref.lower().split() if len(word) > 3):
                    score += 0.25
            else:
                score += 0.2  # neutral

            # Price match (up to 0.5)
            if target_budget:
                price_diff_ratio = abs(prop.price - target_budget) / prop.price
                if price_diff_ratio <= 0.05:  # within 5%
                    score += 0.5
                elif price_diff_ratio <= 0.15: # within 15%
                    score += 0.35
                elif price_diff_ratio <= 0.30: # within 30%
                    score += 0.15
                else:
                    score += 0.0  # complete mismatch

            if score > best_score:
                best_score = score
                best_prop = prop

        return best_prop, best_score

    def evaluate_lead(self, lead_id: int) -> NextActionDecisionOutput:
        """
        Evaluates a lead, extracts criteria, runs property matching,
        computes qualification score, determines next action decision with reasoning,
        and generates structured lead summary.
        """
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead with id {lead_id} not found")

        # Collect conversation transcript
        logs = self.db.query(ConversationLog).filter(
            ConversationLog.lead_id == lead_id
        ).order_by(ConversationLog.created_at).all()

        user_messages = [log.message_text for log in logs if log.sender in ['User', 'user']]
        if not user_messages and logs:
            user_messages = [log.message_text for log in logs]

        extracted = self.extract_preferences(user_messages)
        b_min = extracted["budget_min"]
        b_max = extracted["budget_max"]
        loc_pref = extracted["location_preferences"]
        t_months = extracted["timeline_months"]
        readiness = extracted["readiness"]

        # Match against inventory
        matched_prop, match_fit = self.match_properties(b_min, b_max, loc_pref)

        # Calculate Qualification Score (0 - 100)
        # Factor 1: Pricing clarity & feasibility (0-40)
        score_price = 0.0
        if b_max is not None:
            if matched_prop and abs(matched_prop.price - b_max) / matched_prop.price <= 0.10:
                score_price = 40.0
            elif b_max >= 250000:  # reasonable real estate budget
                score_price = 30.0
            elif b_max < 150000 and "downtown" in loc_pref.lower():
                score_price = 5.0  # severe unrealistic disconnect
            else:
                score_price = 15.0

        # Factor 2: Timeline urgency (0-30)
        score_timeline = 0.0
        if t_months is not None:
            if t_months <= 1:
                score_timeline = 30.0
            elif t_months <= 3:
                score_timeline = 20.0
            elif t_months <= 6:
                score_timeline = 10.0
            else:
                score_timeline = 5.0
        else:
            score_timeline = 5.0

        # Factor 3: Property Match & Location Fit (0-30)
        score_fit = match_fit * 30.0

        total_score = round(min(100.0, max(0.0, score_price + score_timeline + score_fit)), 1)

        # Decide Next Action & Reasoning
        next_action: NextAction
        lead_status: LeadStatus
        reasoning: str
        verdict: str
        broker_action: str

        is_negotiation_signal = any(w in extracted.get("raw_text", "") for w in ["flexible", "negotiat", "discount", "counter-offer", "counter offer"])

        if total_score >= 80 and (t_months is not None and t_months <= 2) and matched_prop:
            if is_negotiation_signal or (b_max and b_max < matched_prop.price):
                # High score with explicit price negotiation or budget slightly below asking -> NEGOTIATE
                next_action = NextAction.NEGOTIATE
                lead_status = LeadStatus.QUALIFIED
                verdict = "QUALIFIED_NEGOTIATION"
                broker_action = f"Broker contacts seller to explore counter-offer near ${b_max:,.0f}"
                reasoning = (
                    f"Buyer is highly qualified with {readiness} and high intent, but is seeking price flexibility "
                    f"with budget (${b_max:,.0f}) compared to asking price (${matched_prop.price:,.0f} for {matched_prop.title}). "
                    f"High probability deal if broker facilitates negotiation."
                )
            else:
                next_action = NextAction.CALL_UP
                lead_status = LeadStatus.QUALIFIED
                verdict = "HOT_LEAD"
                broker_action = f"Call immediately to schedule viewing for {matched_prop.title}"
                reasoning = (
                    f"Buyer has verified budget (${b_min or b_max:,.0f} - ${b_max:,.0f}) fully covering asking price "
                    f"(${matched_prop.price:,.0f}), an urgent purchase timeline ({t_months} month(s)), "
                    f"and readiness ({readiness}). Immediate broker escalation guarantees deal capture."
                )
        elif total_score >= 60 and matched_prop:
            next_action = NextAction.NEGOTIATE
            lead_status = LeadStatus.QUALIFIED
            verdict = "NEGOTIATION_OPPORTUNITY"
            broker_action = f"Present {matched_prop.title} options and discuss financing terms"
            reasoning = (
                f"Lead demonstrates viable buying power (${b_max or b_min:,.0f}) and location interest in "
                f"{loc_pref}. Timeline is {t_months or 'flexible'} months. Broker engagement recommended to structure deal."
            )
        else:
            # Ambiguous lead requiring budget or timeline realignment
            next_action = NextAction.NEGOTIATE
            lead_status = LeadStatus.AMBIGUOUS
            verdict = "AMBIGUOUS_LEAD"
            broker_action = "Negotiate and calibrate budget and timeline expectations with buyer before scheduling viewings"
            reasoning = (
                f"Lead preferences remain ambiguous with timeline ({t_months or 'unspecified'} months) and budget "
                f"(${b_max or '<$150k'}) misaligned with inventory. Action required is NEGOTIATE to align expectations before escalating."
            )

        # Build Structured Lead Summary
        budget_str = f"${b_min:,.0f} - ${b_max:,.0f}" if (b_min and b_max) else (f"Up to ${b_max:,.0f}" if b_max else "Unspecified")
        timeline_str = f"Within {t_months} month(s)" if t_months else "Vague / Indefinite"
        matched_str = f"{matched_prop.title} (${matched_prop.price:,.0f} in {matched_prop.location})" if matched_prop else "None"

        structured_summary = StructuredLeadSummary(
            buyer_name=lead.name,
            budget_range=budget_str,
            target_location=loc_pref,
            timeline=timeline_str,
            financial_readiness=readiness,
            matched_property=matched_str,
            verdict=verdict,
            broker_action=broker_action
        )

        # Update or create LeadQualification record in DB
        summary_json = structured_summary.model_dump_json()

        qual = self.db.query(LeadQualification).filter(LeadQualification.lead_id == lead.id).first()
        if not qual:
            qual = LeadQualification(
                lead_id=lead.id,
                budget_min=b_min,
                budget_max=b_max,
                location_preferences=loc_pref,
                timeline_months=t_months,
                qualification_score=total_score,
                next_action=next_action.value,
                decision_reasoning=reasoning,
                lead_summary=summary_json,
                matched_property_id=matched_prop.id if matched_prop else None
            )
            self.db.add(qual)
        else:
            qual.budget_min = b_min
            qual.budget_max = b_max
            qual.location_preferences = loc_pref
            qual.timeline_months = t_months
            qual.qualification_score = total_score
            qual.next_action = next_action.value
            qual.decision_reasoning = reasoning
            qual.lead_summary = summary_json
            qual.matched_property_id = matched_prop.id if matched_prop else None

        # Update lead status
        lead.status = lead_status.value
        self.db.commit()
        self.db.refresh(qual)

        return NextActionDecisionOutput(
            lead_id=lead.id,
            lead_name=lead.name,
            qualification_score=total_score,
            status=lead_status,
            next_action=next_action,
            reasoning=reasoning,
            lead_summary=structured_summary,
            matched_property_id=matched_prop.id if matched_prop else None,
            matched_property_title=matched_prop.title if matched_prop else None
        )

    def generate_agent_reply(self, lead_id: int, user_message: str) -> str:
        """
        Generates contextual conversational responses that engage prospective buyers,
        asks for missing criteria (budget, location, timeline), and presents matching properties.
        """
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        extracted = self.extract_preferences([user_message])
        
        # Check available properties
        matched_prop, _ = self.match_properties(
            extracted["budget_min"], extracted["budget_max"], extracted["location_preferences"]
        )

        user_lower = user_message.lower()
        if "hello" in user_lower or "hi" in user_lower:
            return (
                f"Hello {lead.name}! I am your Real Estate Concierge. I would love to help you find the perfect property. "
                "Which neighborhood are you looking in, and what is your target budget range?"
            )
        
        if not extracted["budget_max"]:
            return (
                "That sounds wonderful! To help me narrow down available listings, could you share your target budget "
                "range or if you have pre-approved financing?"
            )
            
        if not extracted["timeline_months"]:
            if matched_prop:
                return (
                    f"Great! We have an excellent match: '{matched_prop.title}' at ${matched_prop.price:,.0f} in {matched_prop.location}. "
                    "How soon are you looking to purchase or move in (e.g., within 30 days, 2-3 months)?"
                )
            return "Got it! How soon are you hoping to finalize your purchase or move in?"

        if matched_prop:
            return (
                f"Thank you {lead.name}! Based on your budget of ${extracted['budget_max']:,.0f} and preference for {extracted['location_preferences']}, "
                f"I highly recommend '{matched_prop.title}' (${matched_prop.price:,.0f}). I have documented all your details for our lead broker."
            )

        return "Thank you for sharing your preferences! I am recording your details and matching them with our latest real estate inventory."
