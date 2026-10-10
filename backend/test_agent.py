#!/usr/bin/env python3
"""
Test Suite for Real Estate Lead Qualifier Agent (Member 3)
Covers all 8 required test cases from problem specifications:
1. Complete requirements and a matching property.
2. Missing budget or location.
3. Missing purchase timeline.
4. Conflicting preferences.
5. No matching properties.
6. A buyer interested in purchasing much later.
7. A request explicitly outside the broker's service scope.
8. An LLM API failure.
"""
import os
import sys
import json

# Ensure UTF-8 output encoding across platforms
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.database import SessionLocal
from backend.agent import LeadQualifierAgent
from backend.models import Property, Lead, ConversationLog, LeadQualification

import re

QUESTION_PATTERNS = [
    r'\b(?:how many|what|number of)\s+(?:bedrooms?|bhk)\b',
    r'\bbedroom count\b',
    r'\b(?:pre-approved|preapproved|pre-approval)\b',
    r'\b(?:financial readiness|proof of funds)\b',
    r'\bdo you have (?:a )?loan\b'
]


def assert_negative_constraints(reply: str, case_name: str):
    """Verifies agent NEVER asks about bedroom count, loan pre-approval, or financial readiness."""
    reply_lower = reply.lower()
    for pattern in QUESTION_PATTERNS:
        if re.search(pattern, reply_lower):
            raise AssertionError(f"[{case_name}] Prohibited inquiry matching '{pattern}' found in reply: '{reply}'")



import time


def send_test_message(agent, lead_id: int, message: str, simulate_failure: bool = False):
    """Executes agent.process_message with automatic retry if free-tier rate limits (429) or spikes (503) are encountered."""
    for attempt in range(4):
        res = agent.process_message(lead_id=lead_id, message=message, simulate_llm_failure=simulate_failure)
        if not simulate_failure and any(k in res.reasoning for k in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "high demand"]):
            print(f"  ⏳ Gemini free-tier quota limit or demand spike (429/503) on attempt {attempt+1}. Pausing 10s before retry...")
            time.sleep(10)
            continue
        # Brief pacing between tests
        time.sleep(1.5)
        return res
    return res


def run_tests():
    print("=" * 80)
    print("🧪 RUNNING REAL ESTATE AI LEAD QUALIFIER & MATCHING TEST SUITE")
    print("=" * 80)

    db = SessionLocal()
    agent = LeadQualifierAgent(db)

    results = []

    # ------------------------------------------------------------------
    # Case 1: Complete requirements and a matching property
    # ------------------------------------------------------------------
    print("\n--- TEST 1: Complete requirements and matching property ---")
    lead_id = 101
    msg1 = "I need an apartment in Kakkanad for around 80 lakh, within two months."
    res1 = send_test_message(agent, lead_id=lead_id, message=msg1)
    print(f"Input: '{msg1}'")
    print(f"Status: {res1.lead_status} | Action: {res1.recommended_action} | Priority: {res1.priority}")
    print(f"Extracted: {res1.extracted_preferences.model_dump()}")
    print(f"Matched count: {len(res1.matched_properties)}")
    if res1.matched_properties:
        print(f"Top match: {res1.matched_properties[0]['title']} (${res1.matched_properties[0]['price']:,.0f}, score: {res1.matched_properties[0]['match_score']})")
    print(f"Reply: '{res1.reply}'")

    assert res1.lead_status == "Qualified", f"Expected Qualified, got {res1.lead_status}"
    assert res1.recommended_action == "escalate_to_broker", f"Expected escalate_to_broker, got {res1.recommended_action}"
    assert res1.priority == "High", f"Expected High priority for 2-month timeline, got {res1.priority}"
    assert len(res1.matched_properties) > 0, "Expected at least 1 matching property"
    assert_negative_constraints(res1.reply, "Test 1")
    results.append(("1. Complete requirements and matching property", "PASSED"))

    # ------------------------------------------------------------------
    # Case 2: Missing budget or location
    # ------------------------------------------------------------------
    print("\n--- TEST 2A: Missing budget ---")
    lead_id = 102
    msg2a = "I am looking for an apartment in Kakkanad within two months."
    res2a = send_test_message(agent, lead_id=lead_id, message=msg2a)
    print(f"Input: '{msg2a}'")
    print(f"Status: {res2a.lead_status} | Action: {res2a.recommended_action} | Missing: {res2a.missing_information}")
    print(f"Reply: '{res2a.reply}'")

    assert res2a.lead_status == "Ambiguous", f"Expected Ambiguous, got {res2a.lead_status}"
    assert res2a.recommended_action == "ask_follow_up", f"Expected ask_follow_up, got {res2a.recommended_action}"
    assert "budget" in res2a.missing_information, "Expected 'budget' in missing_information"
    assert_negative_constraints(res2a.reply, "Test 2A")

    print("\n--- TEST 2B: Missing location ---")
    lead_id = 103
    msg2b = "I want an apartment for around 80 lakh within two months."
    res2b = send_test_message(agent, lead_id=lead_id, message=msg2b)
    print(f"Input: '{msg2b}'")
    print(f"Status: {res2b.lead_status} | Action: {res2b.recommended_action} | Missing: {res2b.missing_information}")
    print(f"Reply: '{res2b.reply}'")

    assert res2b.lead_status == "Ambiguous", f"Expected Ambiguous, got {res2b.lead_status}"
    assert res2b.recommended_action == "ask_follow_up", f"Expected ask_follow_up, got {res2b.recommended_action}"
    assert "location" in res2b.missing_information, "Expected 'location' in missing_information"
    assert_negative_constraints(res2b.reply, "Test 2B")
    results.append(("2. Missing budget or location", "PASSED"))

    # ------------------------------------------------------------------
    # Case 3: Missing purchase timeline
    # ------------------------------------------------------------------
    print("\n--- TEST 3: Missing purchase timeline ---")
    lead_id = 104
    msg3 = "I need an apartment in Kakkanad for around 80 lakh."
    res3 = send_test_message(agent, lead_id=lead_id, message=msg3)
    print(f"Input: '{msg3}'")
    print(f"Status: {res3.lead_status} | Action: {res3.recommended_action} | Missing: {res3.missing_information}")
    print(f"Reply: '{res3.reply}'")

    assert res3.lead_status == "Ambiguous", f"Expected Ambiguous, got {res3.lead_status}"
    assert res3.recommended_action == "ask_follow_up", f"Expected ask_follow_up, got {res3.recommended_action}"
    assert "timeline_months" in res3.missing_information, "Expected 'timeline_months' in missing_information"
    assert_negative_constraints(res3.reply, "Test 3")
    results.append(("3. Missing purchase timeline", "PASSED"))

    # ------------------------------------------------------------------
    # Case 4: Conflicting preferences
    # ------------------------------------------------------------------
    print("\n--- TEST 4: Conflicting preferences ---")
    lead_id = 105
    msg4 = "I want a luxury villa in Downtown for 50k, but actually my budget is 2 crore for a penthouse in Marina Bay."
    res4 = send_test_message(agent, lead_id=lead_id, message=msg4)
    print(f"Input: '{msg4}'")
    print(f"Status: {res4.lead_status} | Action: {res4.recommended_action} | Reasoning: {res4.reasoning}")
    print(f"Reply: '{res4.reply}'")

    assert res4.lead_status == "Ambiguous", f"Expected Ambiguous, got {res4.lead_status}"
    assert res4.recommended_action == "ask_follow_up", f"Expected ask_follow_up, got {res4.recommended_action}"
    assert "conflict" in res4.reasoning.lower(), "Expected conflict mentioned in reasoning"
    assert_negative_constraints(res4.reply, "Test 4")
    results.append(("4. Conflicting preferences", "PASSED"))

    # ------------------------------------------------------------------
    # Case 5: No matching properties
    # ------------------------------------------------------------------
    print("\n--- TEST 5: No matching properties ---")
    lead_id = 106
    msg5 = "I want an apartment in Kakkanad with a maximum budget of 15 lakh within 2 months."
    res5 = send_test_message(agent, lead_id=lead_id, message=msg5)
    print(f"Input: '{msg5}'")
    print(f"Status: {res5.lead_status} | Action: {res5.recommended_action} | Matches: {len(res5.matched_properties)}")
    print(f"Reasoning: {res5.reasoning}")
    print(f"Reply: '{res5.reply}'")

    # Constraint: Do not disqualify just because no current property matches!
    assert res5.lead_status != "Disqualified", "Must not disqualify a lead just because no property matches"
    assert res5.lead_status == "Ambiguous", f"Expected Ambiguous, got {res5.lead_status}"
    assert res5.recommended_action == "ask_follow_up", f"Expected ask_follow_up, got {res5.recommended_action}"
    assert len(res5.matched_properties) == 0, "Expected 0 matched properties"
    assert "flexible" in res5.reply.lower() or "alternative" in res5.reply.lower() or "criteria" in res5.reply.lower()
    assert_negative_constraints(res5.reply, "Test 5")
    results.append(("5. No matching properties", "PASSED"))

    # ------------------------------------------------------------------
    # Case 6: A buyer interested in purchasing much later
    # ------------------------------------------------------------------
    print("\n--- TEST 6: Buyer purchasing much later ---")
    lead_id = 107
    msg6 = "I need an apartment in Kakkanad for around 80 lakh, but I am only looking to purchase in 24 months."
    res6 = send_test_message(agent, lead_id=lead_id, message=msg6)
    print(f"Input: '{msg6}'")
    print(f"Status: {res6.lead_status} | Action: {res6.recommended_action} | Priority: {res6.priority}")
    print(f"Timeline months: {res6.extracted_preferences.timeline_months}")
    print(f"Reasoning: {res6.reasoning}")
    print(f"Reply: '{res6.reply}'")

    # Constraint: Do not disqualify a lead just because timeline is long; recommend nurture
    assert res6.lead_status != "Disqualified", "Must not disqualify lead with long timeline"
    assert res6.recommended_action == "nurture", f"Expected nurture, got {res6.recommended_action}"
    assert res6.priority == "Low", f"Expected Low priority for 24-month horizon, got {res6.priority}"
    assert res6.extracted_preferences.timeline_months == 24, "Expected timeline_months == 24"
    assert_negative_constraints(res6.reply, "Test 6")
    results.append(("6. Buyer interested in purchasing much later", "PASSED"))

    # ------------------------------------------------------------------
    # Case 7: Request explicitly outside broker's service scope
    # ------------------------------------------------------------------
    print("\n--- TEST 7: Outside broker's service scope ---")
    lead_id = 108
    msg7 = "I want to rent a commercial shop or warehouse for 25,000 per month."
    res7 = send_test_message(agent, lead_id=lead_id, message=msg7)
    print(f"Input: '{msg7}'")
    print(f"Status: {res7.lead_status} | Action: {res7.recommended_action} | Priority: {res7.priority}")
    print(f"Reasoning: {res7.reasoning}")
    print(f"Reply: '{res7.reply}'")

    assert res7.lead_status == "Disqualified", f"Expected Disqualified, got {res7.lead_status}"
    assert res7.recommended_action == "redirect_or_archive", f"Expected redirect_or_archive, got {res7.recommended_action}"
    assert res7.priority == "Low", f"Expected Low priority, got {res7.priority}"
    assert len(res7.matched_properties) == 0, "Disqualified lead must have 0 matched properties"
    assert_negative_constraints(res7.reply, "Test 7")
    results.append(("7. Request outside broker's service scope", "PASSED"))

    # ------------------------------------------------------------------
    # Case 8: An LLM API failure
    # ------------------------------------------------------------------
    print("\n--- TEST 8: LLM API failure simulation ---")
    lead_id = 109
    msg8 = "I want a luxury apartment in Kakkanad within 2 months."
    res8 = send_test_message(agent, lead_id=lead_id, message=msg8, simulate_failure=True)
    print(f"Input: '{msg8}'")
    print(f"Status: {res8.lead_status} | Action: {res8.recommended_action} | Priority: {res8.priority}")
    print(f"Extracted prefs: {res8.extracted_preferences.model_dump()}")
    print(f"Reasoning: {res8.reasoning}")
    print(f"Reply: '{res8.reply}'")

    # Constraints: Return clear safe follow-up; do NOT claim preferences were successfully extracted
    assert res8.lead_status == "Ambiguous", f"Expected Ambiguous, got {res8.lead_status}"
    assert res8.recommended_action == "ask_follow_up", f"Expected ask_follow_up, got {res8.recommended_action}"
    assert res8.extracted_preferences.budget_max is None, "Budget must not be falsely claimed on API failure"
    assert res8.extracted_preferences.location is None, "Location must not be falsely claimed on API failure"
    assert "error" in res8.reasoning.lower() or "failure" in res8.reasoning.lower(), "Expected error noted in reasoning"
    assert_negative_constraints(res8.reply, "Test 8")
    results.append(("8. LLM API failure", "PASSED"))

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY RESULTS:")
    print("=" * 80)
    all_passed = True
    for name, status in results:
        print(f"  ✅ {name:<50} : {status}")
        if status != "PASSED":
            all_passed = False

    db.close()

    print("=" * 80)
    if all_passed:
        print("🎉 ALL 8 TEST CASES PASSED SUCCESSFULLY!")
    else:
        print("❌ SOME TESTS FAILED.")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
