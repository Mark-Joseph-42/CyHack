-- =====================================================================
-- Real Estate Lead Qualifier - Database Schema
-- Problem #4: Automated Lead Engagement, Qualification & Decision Engine
-- =====================================================================

-- Drop existing tables if re-initializing (in dependency order)
DROP TABLE IF EXISTS conversation_logs;
DROP TABLE IF EXISTS lead_qualifications;
DROP TABLE IF EXISTS leads;
DROP TABLE IF EXISTS properties;

-- =====================================================================
-- 1. PROPERTIES TABLE
-- Stores real estate inventory available for matching against buyer preferences
-- =====================================================================
CREATE TABLE properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    price REAL NOT NULL,
    location VARCHAR(255) NOT NULL,
    bedrooms INTEGER DEFAULT 2,
    property_type VARCHAR(100) DEFAULT 'Apartment',
    description TEXT,
    is_available BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- 2. LEADS TABLE
-- Prospective buyers engaging with the real estate brokerage
-- Status values: 'QUALIFIED', 'AMBIGUOUS'
-- =====================================================================
CREATE TABLE leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'AMBIGUOUS' 
        CHECK (status IN ('QUALIFIED', 'AMBIGUOUS')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- 3. LEAD_QUALIFICATIONS TABLE
-- Captures buyer criteria, AI qualification score, property match,
-- and the Next-Action Decision with comprehensive reasoning + summary
-- Next action values: 'CALL_UP', 'NEGOTIATE'
-- =====================================================================
CREATE TABLE lead_qualifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL UNIQUE,
    budget_min REAL,
    budget_max REAL,
    location_preferences TEXT,
    timeline_months INTEGER,
    qualification_score REAL DEFAULT 0.0 CHECK (qualification_score >= 0.0 AND qualification_score <= 100.0),
    next_action VARCHAR(50) NOT NULL 
        CHECK (next_action IN ('CALL_UP', 'NEGOTIATE')),
    decision_reasoning TEXT NOT NULL,
    lead_summary TEXT NOT NULL,
    matched_property_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
    FOREIGN KEY (matched_property_id) REFERENCES properties(id) ON DELETE SET NULL
);

-- =====================================================================
-- 4. CONVERSATION_LOGS TABLE
-- Complete transcript between prospective buyer and AI Qualifier Agent
-- Sender values: 'User', 'AI Agent'
-- =====================================================================
CREATE TABLE conversation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL,
    lead_name VARCHAR(255) NOT NULL,
    sender VARCHAR(50) NOT NULL CHECK (sender IN ('User', 'AI Agent')),
    message_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

-- =====================================================================
-- INDEXES FOR FAST QUERYING & REPORTING
-- =====================================================================
CREATE INDEX idx_properties_location_price ON properties(location, price);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_qualifications_lead_id ON lead_qualifications(lead_id);
CREATE INDEX idx_qualifications_next_action ON lead_qualifications(next_action);
CREATE INDEX idx_qualifications_score ON lead_qualifications(qualification_score);
CREATE INDEX idx_conversation_lead_id ON conversation_logs(lead_id);

-- =====================================================================
-- SEED DATA: PROPERTIES
-- =====================================================================
INSERT INTO properties (title, price, location, bedrooms, property_type, description) VALUES
('Luxury 3BHK Skyline Penthouse', 850000.00, 'Downtown / Central', 3, 'Penthouse', 'High-rise luxury penthouse with panoramic city views, modern kitchen, and private terrace.'),
('Charming 2BHK Garden Apartment', 420000.00, 'Greenwood Suburb', 2, 'Apartment', 'Spacious garden-facing apartment close to top-rated schools, parks, and commuter transit.'),
('Modern 4BHK Waterfront Villa', 1250000.00, 'Marina Bay', 4, 'Villa', 'Exclusive waterfront villa with private jetty, infinity pool, and smart home automation.'),
('Cozy 1BHK Urban Loft', 280000.00, 'Art District / Midtown', 1, 'Loft', 'Industrial aesthetic loft with exposed brick walls, 14ft ceilings, ideal for young professionals.'),
('Spacious 3BHK Family Townhouse', 550000.00, 'Northwood Estates', 3, 'Townhouse', 'Contemporary suburban townhouse with attached 2-car garage and community clubhouse access.');

-- =====================================================================
-- SEED DATA: LEADS
-- =====================================================================
-- Lead 1: High urgency, exact budget match -> QUALIFIED (CALL_UP)
INSERT INTO leads (id, name, email, phone, status) VALUES
(1, 'Marcus Vance', 'marcus.vance@example.com', '+1-555-0192', 'QUALIFIED');

-- Lead 2: Realistic budget slightly below asking, ready to negotiate -> QUALIFIED (NEGOTIATE)
INSERT INTO leads (id, name, email, phone, status) VALUES
(2, 'Sarah Chen', 'sarah.chen@example.com', '+1-555-0144', 'QUALIFIED');

-- Lead 3: Ambiguous preferences, vague timeline, unrealistic budget -> AMBIGUOUS (DISCARD)
INSERT INTO leads (id, name, email, phone, status) VALUES
(3, 'Alex Mercer', 'alex.mercer@example.com', '+1-555-0188', 'AMBIGUOUS');

-- =====================================================================
-- SEED DATA: CONVERSATION LOGS
-- =====================================================================
-- Conversation for Marcus Vance (Lead 1)
INSERT INTO conversation_logs (lead_id, lead_name, sender, message_text) VALUES
(1, 'Marcus Vance', 'User', 'Hi, I saw your 3BHK penthouse listing in Downtown. Is it still available?'),
(1, 'Marcus Vance', 'AI Agent', 'Hello Marcus! Yes, the 3BHK Skyline Penthouse in Downtown is currently available. To help ensure it is a good fit, what budget range and timeline are you working with?'),
(1, 'Marcus Vance', 'User', 'My budget is between $800k and $900k. I already have pre-approved financing in place and need to relocate and close within the next 30 days.'),
(1, 'Marcus Vance', 'AI Agent', 'That aligns perfectly with the $850k asking price. Would you be open to an immediate private tour with our senior broker this afternoon?'),
(1, 'Marcus Vance', 'User', 'Yes, absolutely. Please have the broker call me as soon as possible.');

-- Conversation for Sarah Chen (Lead 2)
INSERT INTO conversation_logs (lead_id, lead_name, sender, message_text) VALUES
(2, 'Sarah Chen', 'User', 'Interested in the 4BHK Waterfront Villa in Marina Bay.'),
(2, 'Sarah Chen', 'AI Agent', 'Welcome Sarah! The Marina Bay Waterfront Villa is an exceptional property. What is your preferred budget and purchase timeline?'),
(2, 'Sarah Chen', 'User', 'Our maximum budget is $1.15M to $1.2M cash. We are ready to close within 60 days if the seller is flexible on the $1.25M asking price.'),
(2, 'Sarah Chen', 'AI Agent', 'Understood. Since you have cash readiness and a 2-month horizon, let me check with the broker regarding seller negotiation leeway.');

-- Conversation for Alex Mercer (Lead 3)
INSERT INTO conversation_logs (lead_id, lead_name, sender, message_text) VALUES
(3, 'Alex Mercer', 'User', 'Hey, just browsing. Do you have penthouses in Downtown for around $100k?'),
(3, 'Alex Mercer', 'AI Agent', 'Hello Alex! Downtown penthouses typically range from $800k upwards. Are you open to smaller units, or is your budget flexible? Also, what is your timeline?'),
(3, 'Alex Mercer', 'User', 'Not sure, maybe next year or whenever. I definitely do not want to spend more than $100k anywhere.');

-- =====================================================================
-- SEED DATA: LEAD QUALIFICATIONS
-- =====================================================================
-- Lead 1 Qualification (Marcus Vance): High urgency, matches Property 1
INSERT INTO lead_qualifications (
    lead_id, budget_min, budget_max, location_preferences, timeline_months, 
    qualification_score, next_action, decision_reasoning, lead_summary, matched_property_id
) VALUES (
    1, 800000.00, 900000.00, 'Downtown / Central', 1, 95.0, 'CALL_UP',
    'Buyer has pre-approved financing ($800k-$900k) that covers asking price ($850k), urgent 30-day timeline due to relocation, requested immediate contact.',
    '{"buyer_name": "Marcus Vance", "budget_range": "$800,000 - $900,000", "target_location": "Downtown / Central", "timeline": "< 1 month (30 days)", "financial_readiness": "Pre-Approved Financing", "matched_property": "Luxury 3BHK Skyline Penthouse ($850,000)", "verdict": "HOT_LEAD", "broker_action": "Call immediately to confirm viewing today"}',
    1
);

-- Lead 2 Qualification (Sarah Chen): Serious cash buyer seeking negotiation on Property 3
INSERT INTO lead_qualifications (
    lead_id, budget_min, budget_max, location_preferences, timeline_months, 
    qualification_score, next_action, decision_reasoning, lead_summary, matched_property_id
) VALUES (
    2, 1150000.00, 1200000.00, 'Marina Bay', 2, 85.0, 'NEGOTIATE',
    'Buyer is pre-qualified with $1.2M liquid cash and 60-day closing window. Asking price is $1.25M (4% variance). High closing probability if broker facilitates counter-offer.',
    '{"buyer_name": "Sarah Chen", "budget_range": "$1,150,000 - $1,200,000", "target_location": "Marina Bay", "timeline": "2 months (60 days)", "financial_readiness": "Cash Ready", "matched_property": "Modern 4BHK Waterfront Villa ($1,250,000)", "verdict": "QUALIFIED_NEGOTIATION", "broker_action": "Open price discussion with seller and propose $1.2M offer"}',
    3
);

-- Lead 3 Qualification (Alex Mercer): Ambiguous preferences and budget disconnect
INSERT INTO lead_qualifications (
    lead_id, budget_min, budget_max, location_preferences, timeline_months, 
    qualification_score, next_action, decision_reasoning, lead_summary, matched_property_id
) VALUES (
    3, 0.00, 100000.00, 'Downtown / Central', 12, 15.0, 'NEGOTIATE',
    'Lead has ambiguous timeline (>12 months) and unrealistic $100k budget for Downtown. Status is AMBIGUOUS; next action requires broker to NEGOTIATE budget expectations to current inventory before escalating for viewings.',
    '{"buyer_name": "Alex Mercer", "budget_range": "< $100,000", "target_location": "Downtown / Central", "timeline": "> 12 months / Unspecified", "financial_readiness": "Unverified / Non-viable", "matched_property": null, "verdict": "AMBIGUOUS_LEAD", "broker_action": "Negotiate and calibrate budget expectations with buyer before escalating to viewings"}',
    NULL
);
