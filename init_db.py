#!/usr/bin/env python3
"""
Database Initialization Script
Executes schema.sql to initialize SQLite tables and populate realistic seed data
for the Real Estate Lead Qualifier Hackathon solution.
"""
import os
import sqlite3
import json

DB_FILE = "real_estate.db"
SCHEMA_FILE = "schema.sql"


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base_dir, SCHEMA_FILE)
    db_path = os.path.join(base_dir, DB_FILE)

    print(f"📦 Initializing Database from '{SCHEMA_FILE}'...")
    if not os.path.exists(schema_path):
        print(f"❌ Error: {SCHEMA_FILE} not found!")
        return

    # Connect to SQLite and execute schema script
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    cursor.executescript(schema_sql)
    conn.commit()

    print(f"✅ Schema executed successfully into '{DB_FILE}'!\n")

    # Verification queries
    print("=" * 70)
    print("📊 DATABASE SUMMARY & SEED DATA VERIFICATION")
    print("=" * 70)

    # 1. Properties
    cursor.execute("SELECT id, title, price, location FROM properties")
    properties = cursor.fetchall()
    print(f"\n🏠 Properties Loaded ({len(properties)}):")
    for prop in properties:
        print(f"  [{prop[0]}] {prop[1]} - ${prop[2]:,.2f} ({prop[3]})")

    # 2. Leads
    cursor.execute("SELECT id, name, status FROM leads")
    leads = cursor.fetchall()
    print(f"\n👤 Leads ({len(leads)}):")
    for lead in leads:
        print(f"  [{lead[0]}] {lead[1]} | Status: {lead[2]}")

    # 3. Qualifications & Next Actions
    cursor.execute("""
        SELECT lq.lead_id, l.name, lq.qualification_score, lq.next_action, 
               lq.decision_reasoning, lq.lead_summary
        FROM lead_qualifications lq
        JOIN leads l ON lq.lead_id = l.id
    """)
    quals = cursor.fetchall()
    print(f"\n🎯 Next-Action Decisions & Lead Summaries ({len(quals)}):")
    for q in quals:
        lead_id, name, score, action, reasoning, summary_str = q
        print(f"\n  ------------------------------------------------------------")
        print(f"  Lead #{lead_id}: {name}")
        print(f"  Score: {score}/100 | Next Action: {action}")
        print(f"  Reasoning: {reasoning}")
        try:
            summary = json.loads(summary_str)
            print(f"  Structured Lead Summary:")
            print(f"    • Budget: {summary.get('budget_range')}")
            print(f"    • Location: {summary.get('target_location')}")
            print(f"    • Timeline: {summary.get('timeline')}")
            print(f"    • Readiness: {summary.get('financial_readiness')}")
            print(f"    • Match: {summary.get('matched_property')}")
            print(f"    • Verdict: {summary.get('verdict')}")
            print(f"    • Broker Action: {summary.get('broker_action')}")
        except Exception:
            print(f"  Summary: {summary_str}")

    conn.close()
    print("\n" + "=" * 70)
    print("✨ Database setup complete and verified!")
    print("=" * 70)


if __name__ == "__main__":
    main()
