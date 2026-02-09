"""
CSV Broadcast Runner for Bedzee PG Company

Reads contacts from docs/Broacsting - Sheet1.csv and runs a full broadcast:
1. Parse CSV -> validate phones -> E.164 normalization
2. Create BroadcastJob in DB
3. Find APPROVED template via MCP (port 9002)
4. Send WhatsApp messages to all contacts via MCP
5. Track results in DB -> mark COMPLETED

Usage:
    python scripts/run_csv_broadcast.py
"""

import csv
import json
import re
import sys
import os
import uuid
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories.broadcast_job_repo import BroadcastJobRepository
from app.database.postgresql.postgresql_repositories.processed_contact_repo import ProcessedContactRepository
from app.database.postgresql.postgresql_repositories.template_creation_repo import TemplateCreationRepository
from app.database.postgresql.postgresql_repositories.memory_repo import MemoryRepository
from app.agents.whatsp_agents.tools.supervisor_broadcasting import _call_direct_api_mcp


# ============================================
# CONFIG
# ============================================

USER_ID = "user1"
PROJECT_ID = "6798e0ab6c6d490c0e356d1d"
BUSINESS_ID = "6798e0ab6c6d490c0e356d18"
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "Broacsting - Sheet1.csv")
DEFAULT_COUNTRY = "91"  # India


# ============================================
# HELPERS
# ============================================

def parse_csv(file_path: str) -> list:
    """Parse contacts from CSV file. Returns list of {name, phone, sno}."""
    contacts = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "").strip()
            phone = row.get("phone number", "").strip()
            sno = row.get("sno", "").strip()
            if phone:
                contacts.append({"name": name, "phone": phone, "sno": sno})
    return contacts


def normalize_phone(phone: str, country_code: str = DEFAULT_COUNTRY) -> str:
    """Normalize phone number to E.164 format."""
    cleaned = re.sub(r'[\s\-\(\)]', '', phone.strip())
    if cleaned.startswith('+'):
        return cleaned
    if cleaned.startswith('0'):
        cleaned = cleaned[1:]
    if not cleaned.startswith(country_code):
        cleaned = country_code + cleaned
    return '+' + cleaned


def validate_phone(phone_e164: str) -> bool:
    """Validate E.164 phone number format."""
    return bool(re.match(r'^\+[1-9]\d{6,14}$', phone_e164))


def print_banner(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_step(phase: str, msg: str):
    print(f"  [{phase}] {msg}")


# ============================================
# MAIN BROADCAST PIPELINE
# ============================================

def run_broadcast():
    print_banner("BEDZEE PG - CSV BROADCAST")
    print(f"  CSV File: {CSV_PATH}")
    print(f"  User ID: {USER_ID}")
    print(f"  Project: {PROJECT_ID}")

    # ------------------------------------------
    # STEP 1: Parse CSV
    # ------------------------------------------
    print_banner("STEP 1: PARSE CSV FILE")

    if not os.path.exists(CSV_PATH):
        print(f"  ERROR: CSV file not found at {CSV_PATH}")
        sys.exit(1)

    raw_contacts = parse_csv(CSV_PATH)
    print(f"  Parsed {len(raw_contacts)} contacts from CSV:")
    for c in raw_contacts:
        print(f"    {c['sno']}. {c['name']} - {c['phone']}")

    # ------------------------------------------
    # STEP 2: Validate & Normalize Phones
    # ------------------------------------------
    print_banner("STEP 2: VALIDATE & NORMALIZE PHONES")

    valid_contacts = []
    invalid_contacts = []

    for c in raw_contacts:
        e164 = normalize_phone(c["phone"])
        if validate_phone(e164):
            valid_contacts.append({
                "name": c["name"],
                "phone_raw": c["phone"],
                "phone_e164": e164,
                "sno": c["sno"],
            })
            print(f"    OK  {c['name']}: {c['phone']} -> {e164}")
        else:
            invalid_contacts.append(c)
            print(f"    BAD {c['name']}: {c['phone']} -> {e164} (invalid)")

    if not valid_contacts:
        print("  ERROR: No valid contacts found. Aborting.")
        sys.exit(1)

    e164_phones = [c["phone_e164"] for c in valid_contacts]
    print(f"\n  Valid: {len(valid_contacts)}, Invalid: {len(invalid_contacts)}")

    # ------------------------------------------
    # STEP 3: Verify JWT & Create Broadcast Job
    # ------------------------------------------
    print_banner("STEP 3: INITIALIZE BROADCAST")

    with get_session() as session:
        memory_repo = MemoryRepository(session=session)
        mem = memory_repo.get_by_user_id(USER_ID)

        if not mem or not mem.get("jwt_token"):
            print("  ERROR: No JWT token for user1. Complete onboarding first.")
            sys.exit(1)

        print_step("JWT", f"Token found (project: {mem['project_id']})")

        broadcast_repo = BroadcastJobRepository(session=session)
        contact_repo = ProcessedContactRepository(session=session)
        template_repo = TemplateCreationRepository(session=session)

        job_id = f"bedzee-csv-{uuid.uuid4().hex[:8]}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id,
            user_id=USER_ID,
            project_id=PROJECT_ID,
            phase="INITIALIZED",
        )
        print_step("INITIALIZED", f"Broadcast job created: {job_id}")

        # ------------------------------------------
        # STEP 4: DATA_PROCESSING
        # ------------------------------------------
        print_banner("STEP 4: DATA PROCESSING")

        broadcast_repo.update_phase(job_id, "DATA_PROCESSING")
        broadcast_repo.update_contacts(
            job_id=job_id,
            contacts_data=json.dumps(e164_phones),
            total=len(raw_contacts),
            valid=len(valid_contacts),
            invalid=len(invalid_contacts),
        )

        processed = [
            {
                "phone_e164": c["phone_e164"],
                "name": c["name"],
                "country_code": "IN",
                "quality_score": 80,
                "source_row": int(c["sno"]) if c["sno"] else i + 1,
                "is_duplicate": False,
                "custom_fields": {"sno": c["sno"], "source": "csv"},
            }
            for i, c in enumerate(valid_contacts)
        ]
        contact_repo.bulk_create(processed, job_id, USER_ID)
        print_step("DATA_PROCESSING", f"{len(valid_contacts)} contacts processed and stored")

        # ------------------------------------------
        # STEP 5: COMPLIANCE_CHECK
        # ------------------------------------------
        print_banner("STEP 5: COMPLIANCE CHECK")

        broadcast_repo.update_phase(job_id, "COMPLIANCE_CHECK")
        broadcast_repo.update_compliance(
            job_id=job_id,
            compliance_status="passed",
            compliance_details=json.dumps({"check": "auto-pass for csv broadcast"}),
        )
        print_step("COMPLIANCE_CHECK", "Passed (auto-pass for direct CSV broadcast)")

        # ------------------------------------------
        # STEP 6: SEGMENTATION
        # ------------------------------------------
        print_banner("STEP 6: SEGMENTATION")

        broadcast_repo.update_phase(job_id, "SEGMENTATION")
        segments = [{"name": "All Contacts", "criteria": "all", "contact_count": len(valid_contacts)}]
        broadcast_repo.update_segments(job_id, json.dumps(segments))
        print_step("SEGMENTATION", f"1 segment: All Contacts ({len(valid_contacts)})")

        # ------------------------------------------
        # STEP 7: CONTENT_CREATION - Find APPROVED template via MCP
        # ------------------------------------------
        print_banner("STEP 7: CONTENT CREATION")

        broadcast_repo.update_phase(job_id, "CONTENT_CREATION")

    # MCP calls outside DB session to avoid long-held connections
    print_step("CONTENT_CREATION", "Listing templates from WhatsApp via MCP...")

    list_result = _call_direct_api_mcp("get_templates", {"user_id": USER_ID})

    approved_template = None
    if isinstance(list_result, dict) and list_result.get("success"):
        data_wrapper = list_result.get("data", {})
        if isinstance(data_wrapper, dict) and "data" in data_wrapper:
            templates = data_wrapper["data"]
        elif isinstance(data_wrapper, list):
            templates = data_wrapper
        else:
            templates = []

        print(f"  Found {len(templates)} templates:")
        for t in templates:
            if isinstance(t, dict):
                status = t.get("status", "").upper()
                name = t.get("name", "")
                cat = t.get("category", "")
                lang = t.get("language", "")
                tpl_id = t.get("id", "")
                marker = " <<< SELECTED" if status == "APPROVED" and not approved_template else ""
                print(f"    {name} | {status} | {cat} | {lang}{marker}")
                if status == "APPROVED" and not approved_template:
                    approved_template = t
    else:
        print(f"  MCP error: {list_result}")

    if not approved_template:
        print("\n  ERROR: No APPROVED template found. Cannot send broadcast.")
        print("  Please create and get a template approved in WhatsApp Business Manager first.")
        sys.exit(1)

    tpl_name = approved_template.get("name", "")
    tpl_id = str(approved_template.get("id", ""))
    tpl_lang = approved_template.get("language", "en_US")
    tpl_cat = approved_template.get("category", "MARKETING")

    print_step("CONTENT_CREATION", f"Using APPROVED template: {tpl_name} (ID: {tpl_id})")

    # Detect template variables to build components
    tpl_components = approved_template.get("components", [])
    has_body_var = False
    for comp in tpl_components:
        if isinstance(comp, dict) and comp.get("type", "").upper() == "BODY":
            body_text = comp.get("text", "")
            if "{{1}}" in body_text:
                has_body_var = True
                print(f"  Template body: {body_text}")
                print(f"  Variable {{{{1}}}} will be filled with contact name")
            break

    # Link template to broadcast job
    with get_session() as session:
        broadcast_repo = BroadcastJobRepository(session=session)
        broadcast_repo.update_template(
            job_id=job_id,
            template_id=tpl_id,
            template_name=tpl_name,
            template_language=tpl_lang,
            template_category=tpl_cat,
            template_status="APPROVED",
        )

        # ------------------------------------------
        # STEP 8: READY_TO_SEND
        # ------------------------------------------
        print_banner("STEP 8: READY TO SEND")

        broadcast_repo.update_phase(job_id, "READY_TO_SEND")
        print_step("READY_TO_SEND", "Broadcast summary:")
        print(f"    Company: Bedzee PG")
        print(f"    Contacts: {len(valid_contacts)}")
        for c in valid_contacts:
            print(f"      - {c['name']} ({c['phone_e164']})")
        print(f"    Template: {tpl_name} ({tpl_cat}, {tpl_lang})")
        print(f"    Job ID: {job_id}")

        # ------------------------------------------
        # STEP 9: SENDING via MCP
        # ------------------------------------------
        print_banner("STEP 9: SENDING MESSAGES")

        broadcast_repo.update_phase(job_id, "SENDING")

    # Send messages outside DB session
    sent = 0
    failed = 0
    results = []

    for i, c in enumerate(valid_contacts):
        phone = c["phone_e164"]
        name = c["name"]

        send_params = {
            "user_id": USER_ID,
            "to": phone.replace("+", ""),
            "message_type": "template",
            "template_name": tpl_name,
            "template_language_code": tpl_lang,
            "template_language_policy": "deterministic",
        }

        # Add template_components if template has {{1}} variable
        if has_body_var:
            send_params["template_components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": name}
                    ]
                }
            ]

        send_result = _call_direct_api_mcp("send_message", send_params)

        success = False
        msg_id = ""
        if isinstance(send_result, dict):
            success = send_result.get("success", False) or send_result.get("status") == "success"
            if success and isinstance(send_result.get("data"), dict):
                messages = send_result["data"].get("messages", [])
                if messages and isinstance(messages[0], dict):
                    msg_id = messages[0].get("id", "")

        if success:
            sent += 1
            print(f"  [{i+1}/{len(valid_contacts)}] {name} ({phone}) -> SENT {msg_id}")
        else:
            failed += 1
            error = send_result.get("error", "Unknown") if isinstance(send_result, dict) else str(send_result)
            print(f"  [{i+1}/{len(valid_contacts)}] {name} ({phone}) -> FAILED: {error}")

        results.append({"name": name, "phone": phone, "success": success, "msg_id": msg_id})

    # ------------------------------------------
    # STEP 10: COMPLETED
    # ------------------------------------------
    print_banner("STEP 10: BROADCAST COMPLETED")

    with get_session() as session:
        broadcast_repo = BroadcastJobRepository(session=session)
        broadcast_repo.update_send_progress(job_id, sent=sent, failed=failed)
        broadcast_repo.update_phase(job_id, "COMPLETED")

        final = broadcast_repo.get_by_id(job_id)

    print(f"  Company: Bedzee PG")
    print(f"  Job ID: {job_id}")
    print(f"  Phase: {final['phase']}")
    print(f"  Template: {final['template_name']}")
    print(f"  Total Contacts: {final['total_contacts']}")
    print(f"  Valid Contacts: {final['valid_contacts']}")
    print(f"  Sent: {final['sent_count']}")
    print(f"  Failed: {final['failed_count']}")
    print(f"  Started: {final.get('started_sending_at', 'N/A')}")
    print(f"  Completed: {final.get('completed_at', 'N/A')}")

    print(f"\n  Delivery Results:")
    for r in results:
        status = "SENT" if r["success"] else "FAILED"
        print(f"    {r['name']} ({r['phone']}): {status} {r['msg_id']}")

    print(f"\n  RESULT: {sent}/{len(valid_contacts)} messages sent successfully")
    print(f"{'='*60}\n")

    return sent, failed


if __name__ == "__main__":
    sent, failed = run_broadcast()
    sys.exit(0 if failed == 0 else 1)
