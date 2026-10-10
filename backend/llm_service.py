from ast import Tuple
import os
import re
import json
import logging
from typing import List, Dict, Any, Optional

try:
    from dotenv import load_dotenv
    # Load .env from backend directory or project root
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Custom exception for LLM failures
class LLMServiceError(Exception):
    """Raised when the LLM API call fails."""
    pass


PROHIBITED_TERMS = [
    "bedroom", "bedrooms", "bhk",
    "pre-approval", "preapproved", "pre-approved", "loan pre-approval",
    "financial readiness", "proof of funds", "financing status"
]


def sanitize_reply(text: str) -> str:
    """
    Ensures no questions about bedroom count, loan pre-approval,
    or financial readiness are ever sent to the buyer.
    """
    cleaned = text
    # Remove any sentence asking about bedrooms/BHK
    cleaned = re.sub(r'([^.?!]*\b(?:bedroom|bedrooms|bhk)\b[^.?!]*[.?!]?)', '', cleaned, flags=re.IGNORECASE)
    # Remove any sentence asking about loan/pre-approval/financial readiness
    cleaned = re.sub(r'([^.?!]*\b(?:pre-approval|preapproved|pre-approved|financial readiness|proof of funds)\b[^.?!]*[.?!]?)', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    if not cleaned:
        cleaned = "Could you please specify your preferred location, budget range, and desired purchase timeline?"
    return cleaned


def parse_numeric_budget(text: str) -> Dict[str, Optional[float]]:
    """
    Parses budget mentions supporting Indian numbering (Lakhs, Crores)
    and Western numbering (k, M, $, thousand, million).
    """
    t = text.lower()
    b_min = None
    b_max = None

    # 1. Lakhs and Crores regex
    # Matches e.g. "80 lakh", "80 lakhs", "1.5 crore", "1.5 cr", "70 to 80 lakh", "between 70 and 80 lakh"
    range_lakh = re.search(r'(?:between|from)?\s*(\d+(?:\.\d+)?)\s*(?:to|-|and)\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b', t)
    if range_lakh:
        b_min = float(range_lakh.group(1)) * 100000
        b_max = float(range_lakh.group(2)) * 100000
        return {"budget_min": b_min, "budget_max": b_max}

    range_cr = re.search(r'(?:between|from)?\s*(\d+(?:\.\d+)?)\s*(?:to|-|and)\s*(\d+(?:\.\d+)?)\s*(?:crore|crores|cr)\b', t)
    if range_cr:
        b_min = float(range_cr.group(1)) * 10000000
        b_max = float(range_cr.group(2)) * 10000000
        return {"budget_min": b_min, "budget_max": b_max}

    single_lakh = re.search(r'(?:around|about|under|up to|max(?:imum)?|budget of)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b', t)
    if single_lakh:
        val = float(single_lakh.group(1)) * 100000
        return {"budget_min": None, "budget_max": val}

    single_cr = re.search(r'(?:around|about|under|up to|max(?:imum)?|budget of)?\s*(\d+(?:\.\d+)?)\s*(?:crore|crores|cr)\b', t)
    if single_cr:
        val = float(single_cr.group(1)) * 10000000
        return {"budget_min": None, "budget_max": val}

    # 2. Western numbers (k, m, million, $, commas)
    # Range: e.g. "between $800k and $900k", "800k to 900k", "$1.15M to $1.2M"
    range_western = re.search(r'(?:between|from)?\s*\$?(\d+(?:\.\d+)?)\s*(k|m|million|thousand)?\s*(?:to|-|and)\s*\$?(\d+(?:\.\d+)?)\s*(k|m|million|thousand)\b', t)
    if range_western:
        v1 = float(range_western.group(1))
        u1 = range_western.group(2) or range_western.group(4)
        v2 = float(range_western.group(3))
        u2 = range_western.group(4)

        mult1 = 1000000 if u1 in ['m', 'million'] else (1000 if u1 in ['k', 'thousand'] else 1)
        mult2 = 1000000 if u2 in ['m', 'million'] else (1000 if u2 in ['k', 'thousand'] else 1)
        return {"budget_min": v1 * mult1, "budget_max": v2 * mult2}

    # Single amount: e.g. "$850k", "$850,000", "280k", "1.25M"
    singles = re.findall(r'(?:\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|million|thousand)?|(\d+(?:\.\d+)?)\s*(k|m|million|thousand))', t)
    amounts = []
    for match in singles:
        v_str = match[0] or match[2]
        u_str = match[1] or match[3]
        v_str = v_str.replace(',', '')
        try:
            val = float(v_str)
            mult = 1000000 if u_str in ['m', 'million'] else (1000 if u_str in ['k', 'thousand'] else 1)
            amounts.append(val * mult)
        except ValueError:
            continue

    if amounts:
        if len(amounts) == 1:
            return {"budget_min": None, "budget_max": amounts[0]}
        else:
            return {"budget_min": min(amounts), "budget_max": max(amounts)}

    # Direct large numbers (e.g. 8000000, 850000)
    raw_nums = re.findall(r'\b(\d{5,9})\b', t)
    if raw_nums:
        nums = [float(n) for n in raw_nums]
        if len(nums) == 1:
            return {"budget_min": None, "budget_max": nums[0]}
        return {"budget_min": min(nums), "budget_max": max(nums)}

    return {"budget_min": None, "budget_max": None}


def parse_timeline(text: str) -> Optional[int]:
    """Parses purchase timeline into months."""
    t = text.lower()
    if re.search(r'\b(?:30 days|1 month|one month|this month|immediately|urgent|asap)\b', t):
        return 1
    if re.search(r'\b(?:60 days|2 months|two months)\b', t):
        return 2
    if re.search(r'\b(?:90 days|3 months|three months|a quarter)\b', t):
        return 3
    if re.search(r'\b(?:6 months|six months|half a year)\b', t):
        return 6
    if re.search(r'\b(?:12 months|twelve months|1 year|one year|next year)\b', t):
        return 12
    if re.search(r'\b(?:24 months|2 years|two years)\b', t):
        return 24
    match_months = re.search(r'(\d+)\s*(?:months?|mths?)\b', t)
    if match_months:
        return int(match_months.group(1))
    match_years = re.search(r'(\d+)\s*(?:years?|yrs?)\b', t)
    if match_years:
        return int(match_years.group(1)) * 12
    if any(phrase in t for phrase in ["just browsing", "not sure", "whenever", "sometime later", "in the future"]):
        return 12
    return None


def parse_property_type(text: str) -> Optional[str]:
    """Extracts property type."""
    t = text.lower()
    if "penthouse" in t:
        return "penthouse"
    if "villa" in t:
        return "villa"
    if "townhouse" in t or "town home" in t:
        return "townhouse"
    if "loft" in t:
        return "loft"
    if "apartment" in t or "flat" in t:
        return "apartment"
    if "house" in t or "bungalow" in t or "duplex" in t:
        return "house"
    return None


def parse_location(text: str) -> Optional[str]:
    """Extracts preferred location."""
    t = text.lower()
    known_locations = [
        "kakkanad", "downtown", "greenwood", "marina bay", "art district",
        "midtown", "northwood", "infopark", "kochi", "marine drive",
        "edappally", "aluva", "central"
    ]
    for loc in known_locations:
        if loc in t:
            if loc == "downtown" or loc == "central":
                return "Downtown / Central"
            if loc == "art district" or loc == "midtown":
                return "Art District / Midtown"
            if loc == "greenwood":
                return "Greenwood Suburb"
            if loc == "northwood":
                return "Northwood Estates"
            if loc == "kakkanad":
                return "Kakkanad"
            return loc.title()
    
    # Generic regex for "in <Location>"
    loc_match = re.search(r'\bin\s+([A-Z][a-zA-Z\s]{2,20})(?:\s+for|\s+within|\s+around|[.,]|$)', text)
    if loc_match:
        loc_candidate = loc_match.group(1).strip()
        if loc_candidate.lower() not in ["two", "one", "three", "two months", "a hurry", "around"]:
            return loc_candidate
    return None


def check_outside_scope(text: str) -> Tuple[bool, Optional[str]]:
    """Checks if inquiry is outside the broker's residential sales scope."""
    t = text.lower()
    rental_keywords = ["rent", "lease", "pg", "hostel", "monthly rent", "renting", "for rent"]
    for kw in rental_keywords:
        if re.search(rf'\b{kw}\b', t):
            return True, "Broker specializes exclusively in residential property purchases and sales; rental services are outside our service scope."

    commercial_keywords = ["commercial", "office space", "warehouse", "shop for rent", "retail shop", "industrial land", "factory"]
    for kw in commercial_keywords:
        if kw in t:
            return True, "Broker specializes exclusively in residential homes; commercial and industrial properties are outside our service scope."

    agricultural_keywords = ["agricultural land", "farmland", "farm land", "acres of farm", "plantation"]
    for kw in agricultural_keywords:
        if kw in t:
            return True, "Agricultural and farm land transactions are outside our brokerage service scope."

    non_real_estate = ["car", "used car", "automobile", "laptop", "bitcoin", "crypto", "iphone"]
    for kw in non_real_estate:
        if re.search(rf'\b{kw}\b', t):
            return True, "Request is not related to real estate brokerage."

    if len(text.strip()) < 4 or re.match(r'^[a-z]{5,}$', text.strip()) and text.strip() not in ["hello", "house", "villa"]:
        return True, "Invalid or unparseable inquiry."

    return False, None


def check_conflicting_preferences(text: str) -> bool:
    """Detects mutually contradictory preferences."""
    t = text.lower()
    # Conflicting locations
    locs_found = [loc for loc in ["kakkanad", "downtown", "marina bay", "antarctica"] if loc in t]
    if len(locs_found) > 1 and "or" not in t and "either" not in t:
        return True
    # Conflicting property types
    types_found = [pt for pt in ["penthouse", "villa", "apartment"] if pt in t]
    if len(types_found) > 1 and "or" not in t and "either" not in t:
        return True
    # Drastic budget conflict
    if "50k" in t and ("2 crore" in t or "2cr" in t or "1m" in t):
        return True
    return False


def fallback_extract_preferences(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Robust rule-based preference extractor used when no LLM API key is configured.
    Maintains context from all user messages.
    """
    all_user_text = " ".join([m["content"] for m in messages if m.get("role") in ["user", "User"]]).strip()
    if not all_user_text and messages:
        all_user_text = " ".join([m["content"] for m in messages]).strip()

    latest_message = messages[-1]["content"] if messages else ""

    is_outside, scope_reason = check_outside_scope(latest_message or all_user_text)
    is_conflicting = check_conflicting_preferences(all_user_text)

    budget_info = parse_numeric_budget(all_user_text)
    location = parse_location(all_user_text)
    property_type = parse_property_type(all_user_text)
    timeline_months = parse_timeline(all_user_text)

    missing_fields = []
    if budget_info["budget_max"] is None:
        missing_fields.append("budget")
    if location is None:
        missing_fields.append("location")
    if timeline_months is None:
        missing_fields.append("timeline_months")
    if property_type is None:
        missing_fields.append("property_type")

    # Generate compliant reply (NEVER asking bedrooms, loans, financial readiness)
    if is_outside:
        reply = (
            f"Thank you for contacting us. {scope_reason} "
            "We would be delighted to assist you with any residential property purchase inquiries in our serviced areas."
        )
    elif is_conflicting:
        reply = (
            "I noticed you mentioned different preferences. To help find the best match, "
            "could you clarify your preferred location and budget range?"
        )
    elif missing_fields:
        if "location" in missing_fields and "budget" in missing_fields:
            reply = "Could you please share your target budget and the location you are interested in?"
        elif "budget" in missing_fields:
            reply = "Which budget range are you looking to stay within for this property?"
        elif "location" in missing_fields:
            reply = "Which specific neighborhood or location do you prefer?"
        elif "timeline_months" in missing_fields:
            reply = "What is your anticipated purchase timeline (for instance, within 1-2 months, 6 months, or next year)?"
        else:
            reply = "Could you specify what type of property you are looking for (such as an apartment or villa)?"
    else:
        reply = (
            f"I have noted your requirement for a {property_type or 'property'} in {location} "
            f"around {budget_info['budget_max']:,.0f} within {timeline_months} month(s). Let me find matching listings for you."
        )

    return {
        "budget_min": budget_info["budget_min"],
        "budget_max": budget_info["budget_max"],
        "location": location,
        "property_type": property_type,
        "timeline_months": timeline_months,
        "is_outside_scope": is_outside,
        "is_conflicting": is_conflicting,
        "missing_information": missing_fields,
        "suggested_reply": sanitize_reply(reply),
        "source": "fallback_rule_based"
    }


def call_llm_api(messages: List[Dict[str, str]], simulate_failure: bool = False) -> Dict[str, Any]:
    """
    Calls the configured LLM API (Gemini, OpenAI, or Groq) to extract requirements.
    Falls back to rule-based parser if no API key is set.
    Raises LLMServiceError if configured API fails or simulate_failure is True.
    """
    if simulate_failure or os.getenv("LLM_SIMULATE_FAILURE", "").lower() in ["true", "1", "yes"]:
        raise LLMServiceError("Simulated LLM API failure: Service connection timed out.")

    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    generic_key = os.getenv("LLM_API_KEY")
    provider = os.getenv("LLM_PROVIDER", "auto").lower()

    # Determine active provider
    if provider == "fallback":
        return fallback_extract_preferences(messages)

    if not (gemini_key or openai_key or groq_key or generic_key):
        # Graceful fallback mode when no API key is configured
        return fallback_extract_preferences(messages)

    # Build conversation context transcript
    transcript_lines = []
    for m in messages:
        role = "Buyer" if m.get("role") in ["user", "User"] else "Assistant"
        transcript_lines.append(f"{role}: {m.get('content', '')}")
    transcript_str = "\n".join(transcript_lines)

    system_prompt = (
        "You are an expert AI Real Estate Lead Qualification Agent.\n"
        "Your task is to analyze the conversation between the prospective buyer and the assistant, "
        "extract the buyer's preferences, check whether the request is within broker scope, identify missing or conflicting info, "
        "and produce a natural follow-up or reply.\n\n"
        "STRICT CONSTRAINTS (CRITICAL - NEVER VIOLATE):\n"
        "1. NEVER ask about bedroom count, BHK, or number of rooms.\n"
        "2. NEVER ask about loan pre-approval, mortgage status, or bank approval.\n"
        "3. NEVER ask about financial readiness, cash proof, or funds availability.\n"
        "Only ask clarifying questions about missing budget, preferred location, property type, timeline, or flexibility.\n\n"
        "EXTRACTION RULES:\n"
        "- budget_min (float or null): Minimum budget. If in Lakhs (1 Lakh = 100,000) or Crores (1 Crore = 10,000,000), convert to raw numeric value. E.g. '80 lakh' -> 8000000.\n"
        "- budget_max (float or null): Maximum budget. E.g. '80 lakh' -> 8000000. If single budget stated like 'around 80 lakh', set budget_max: 8000000, budget_min: null.\n"
        "- location (string or null): Locality or city name (e.g., 'Kakkanad', 'Downtown').\n"
        "- property_type (string or null): E.g., 'apartment', 'villa', 'penthouse', 'townhouse', 'loft'.\n"
        "- timeline_months (integer or null): Buying timeline in months (e.g. 'two months' -> 2, '30 days' -> 1, 'next year' -> 12).\n"
        "- is_outside_scope (boolean): TRUE if the request is for rental/lease, commercial/industrial property, agricultural/farmland, non-real estate, or spam. The broker only deals with residential property sales.\n"
        "- is_conflicting (boolean): TRUE if the buyer has stated conflicting budgets, locations, or property types.\n"
        "- missing_information (list of strings): List missing required criteria among ['budget', 'location', 'timeline_months', 'property_type'].\n"
        "- suggested_reply (string): A helpful, polite, natural conversational reply. If criteria are missing, ask for them (obeying constraints). If outside scope, explain scope politely.\n\n"
        "Respond ONLY with a JSON object matching this schema:\n"
        "{\n"
        '  "budget_min": float or null,\n'
        '  "budget_max": float or null,\n'
        '  "location": string or null,\n'
        '  "property_type": string or null,\n'
        '  "timeline_months": integer or null,\n'
        '  "is_outside_scope": boolean,\n'
        '  "is_conflicting": boolean,\n'
        '  "missing_information": string[],\n'
        '  "suggested_reply": string\n'
        "}"
    )

    prompt = f"{system_prompt}\n\nCONVERSATION TRANSCRIPT:\n{transcript_str}\n\nJSON Output:"

    raw_json_str = None

    import time

    # 1. Try Google Gemini
    if (provider in ["auto", "gemini"] and (gemini_key or generic_key)):
        for attempt in range(2):
            try:
                from google import genai
                from google.genai import types
                api_key = gemini_key or generic_key
                client = genai.Client(api_key=api_key)
                model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                raw_json_str = response.text
                break
            except Exception as e:
                err_str = str(e)
                if any(k in err_str for k in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "high demand"]) and attempt == 0:
                    logger.warning("Gemini 429/503 transient limit encountered. Waiting 10s before retry...")
                    time.sleep(10)
                    continue
                logger.error(f"Gemini API error: {e}")
                raise LLMServiceError(f"Gemini API call failed: {e}")

    # 2. Try OpenAI
    elif (provider in ["auto", "openai"] and (openai_key or generic_key)):
        for attempt in range(2):
            try:
                import openai
                api_key = openai_key or generic_key
                client = openai.OpenAI(api_key=api_key)
                model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"CONVERSATION TRANSCRIPT:\n{transcript_str}"}
                    ],
                    response_format={"type": "json_object"}
                )
                raw_json_str = response.choices[0].message.content
                break
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "rate limit" in err_str.lower()) and attempt == 0:
                    logger.warning("OpenAI 429 rate limit encountered. Waiting 5s before retry...")
                    time.sleep(5)
                    continue
                logger.error(f"OpenAI API error: {e}")
                raise LLMServiceError(f"OpenAI API call failed: {e}")

    # 3. Try Groq
    elif (provider in ["auto", "groq"] and (groq_key or generic_key)):
        for attempt in range(2):
            try:
                import groq
                api_key = groq_key or generic_key
                client = groq.Groq(api_key=api_key)
                model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"CONVERSATION TRANSCRIPT:\n{transcript_str}"}
                    ],
                    response_format={"type": "json_object"}
                )
                raw_json_str = response.choices[0].message.content
                break
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "rate limit" in err_str.lower()) and attempt == 0:
                    logger.warning("Groq 429 rate limit encountered. Waiting 5s before retry...")
                    time.sleep(5)
                    continue
                logger.error(f"Groq API error: {e}")
                raise LLMServiceError(f"Groq API call failed: {e}")

    if not raw_json_str:
        return fallback_extract_preferences(messages)

    try:
        # Strip potential markdown code fences
        cleaned_json = re.sub(r'^```json\s*', '', raw_json_str.strip())
        cleaned_json = re.sub(r'\s*```$', '', cleaned_json.strip())
        parsed = json.loads(cleaned_json)
        parsed["suggested_reply"] = sanitize_reply(parsed.get("suggested_reply", ""))
        parsed["source"] = "llm_api"
        return parsed
    except Exception as parse_err:
        logger.warning(f"Failed to parse LLM JSON response: {parse_err}. Content: {raw_json_str}")
        raise LLMServiceError(f"Invalid JSON returned by LLM: {parse_err}")
