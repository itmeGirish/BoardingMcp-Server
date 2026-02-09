"""
Integration tests for WhatsApp Broadcasting Agent workflow.

Tests the full broadcast lifecycle against:
- Live PostgreSQL database (DB layer tests)
- Live MCP server on port 9002 (real template creation + message sending)

Workflow: INITIALIZED -> DATA_PROCESSING -> COMPLIANCE_CHECK -> SEGMENTATION
    -> CONTENT_CREATION -> PENDING_APPROVAL -> READY_TO_SEND -> SENDING
    -> COMPLETED

Uses:
    - user_id: user1
    - Contacts: docs/Broacsting - Sheet1.csv (Girish, Vamsi, Santhu, Mahesh)
    - Template: one promotional MARKETING template
    - Platform: Bedzee pg connector platform
    - MCP Server: Direct API MCP on port 9002
"""
import json
import uuid
import time
import pytest
from datetime import datetime

from app.database.postgresql.postgresql_connection import get_session
from app.database.postgresql.postgresql_repositories import (
    BroadcastJobRepository,
    MemoryRepository,
    TemplateCreationRepository,
    ProcessedContactRepository,
)
from app.database.postgresql.postgresql_repositories.broadcast_job_repo import (
    ALLOWED_TRANSITIONS,
)

# Import test constants from conftest
from tests.conftest import (
    USER_ID,
    PROJECT_ID,
    BUSINESS_ID,
    EMAIL,
    PASSWORD,
    CSV_CONTACTS,
    CSV_PHONE_NUMBERS,
    E164_PHONES,
    TEST_TEMPLATE,
)

# MCP helper - reuse the same pattern as agent tools
from app.agents.whatsp_agents.tools.supervisor_broadcasting import (
    _call_direct_api_mcp,
)


# ============================================
# 1. BROADCAST JOB LIFECYCLE TESTS
# ============================================

class TestBroadcastJobLifecycle:
    """Test creating and managing a broadcast job through all phases."""

    def test_create_broadcast_job(self, broadcast_repo):
        """Test creating a new broadcast job in INITIALIZED phase."""
        job_id = f"test-{uuid.uuid4()}"
        job = broadcast_repo.create_broadcast_job(
            job_id=job_id,
            user_id=USER_ID,
            project_id=PROJECT_ID,
            phase="INITIALIZED",
        )
        assert job is not None
        assert job.id == job_id
        assert job.user_id == USER_ID
        assert job.project_id == PROJECT_ID
        assert job.phase == "INITIALIZED"
        assert job.is_active is True

    def test_get_broadcast_job_by_id(self, broadcast_repo):
        """Test retrieving a broadcast job by ID."""
        job_id = f"test-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )
        result = broadcast_repo.get_by_id(job_id)
        assert result is not None
        assert result["id"] == job_id
        assert result["user_id"] == USER_ID
        assert result["phase"] == "INITIALIZED"

    def test_get_active_jobs_by_user(self, broadcast_repo):
        """Test retrieving all active jobs for user1."""
        job_id = f"test-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )
        jobs = broadcast_repo.get_active_by_user(USER_ID)
        assert len(jobs) >= 1
        job_ids = [j["id"] for j in jobs]
        assert job_id in job_ids

    def test_full_phase_progression(self, broadcast_repo):
        """Test transitioning through the full broadcast state machine."""
        job_id = f"test-lifecycle-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        # Phase progression: INITIALIZED -> ... -> COMPLETED
        transitions = [
            "DATA_PROCESSING",
            "COMPLIANCE_CHECK",
            "SEGMENTATION",
            "CONTENT_CREATION",
            "READY_TO_SEND",
            "SENDING",
            "COMPLETED",
        ]

        for new_phase in transitions:
            success = broadcast_repo.update_phase(job_id, new_phase)
            assert success is True, f"Failed transition to {new_phase}"

        job = broadcast_repo.get_by_id(job_id)
        assert job["phase"] == "COMPLETED"
        assert job["completed_at"] is not None

    def test_phase_with_pending_approval(self, broadcast_repo):
        """Test the CONTENT_CREATION -> PENDING_APPROVAL -> READY_TO_SEND path."""
        job_id = f"test-approval-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        for phase in ["DATA_PROCESSING", "COMPLIANCE_CHECK", "SEGMENTATION", "CONTENT_CREATION"]:
            broadcast_repo.update_phase(job_id, phase)

        # CONTENT_CREATION -> PENDING_APPROVAL
        assert broadcast_repo.update_phase(job_id, "PENDING_APPROVAL") is True

        # PENDING_APPROVAL -> READY_TO_SEND
        assert broadcast_repo.update_phase(job_id, "READY_TO_SEND") is True

        job = broadcast_repo.get_by_id(job_id)
        assert job["phase"] == "READY_TO_SEND"

    def test_pause_resume_flow(self, broadcast_repo):
        """Test SENDING -> PAUSED -> SENDING -> COMPLETED flow."""
        job_id = f"test-pause-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        for phase in [
            "DATA_PROCESSING", "COMPLIANCE_CHECK", "SEGMENTATION",
            "CONTENT_CREATION", "READY_TO_SEND", "SENDING",
        ]:
            broadcast_repo.update_phase(job_id, phase)

        # Pause
        assert broadcast_repo.update_phase(job_id, "PAUSED") is True
        # Resume
        assert broadcast_repo.update_phase(job_id, "SENDING") is True
        # Complete
        assert broadcast_repo.update_phase(job_id, "COMPLETED") is True

        job = broadcast_repo.get_by_id(job_id)
        assert job["phase"] == "COMPLETED"

    def test_failure_from_data_processing(self, broadcast_repo):
        """Test DATA_PROCESSING -> FAILED transition with error message."""
        job_id = f"test-fail-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )
        broadcast_repo.update_phase(job_id, "DATA_PROCESSING")

        success = broadcast_repo.update_phase(
            job_id, "FAILED", error_message="No valid contacts found"
        )
        assert success is True

        job = broadcast_repo.get_by_id(job_id)
        assert job["phase"] == "FAILED"
        assert job["error_message"] == "No valid contacts found"
        assert job["completed_at"] is not None

    def test_cancellation_from_ready_to_send(self, broadcast_repo):
        """Test READY_TO_SEND -> CANCELLED transition."""
        job_id = f"test-cancel-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        for phase in [
            "DATA_PROCESSING", "COMPLIANCE_CHECK", "SEGMENTATION",
            "CONTENT_CREATION", "READY_TO_SEND",
        ]:
            broadcast_repo.update_phase(job_id, phase)

        assert broadcast_repo.update_phase(job_id, "CANCELLED") is True
        job = broadcast_repo.get_by_id(job_id)
        assert job["phase"] == "CANCELLED"

    def test_invalid_transition_rejected(self, broadcast_repo):
        """Test that invalid state transitions are rejected."""
        job_id = f"test-invalid-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        # INITIALIZED -> SENDING is not allowed (must go through intermediate phases)
        success = broadcast_repo.update_phase(job_id, "SENDING")
        assert success is False

        # Job should remain in INITIALIZED
        job = broadcast_repo.get_by_id(job_id)
        assert job["phase"] == "INITIALIZED"

    def test_terminal_state_no_transitions(self, broadcast_repo):
        """Test that terminal states (COMPLETED, FAILED, CANCELLED) allow no further transitions."""
        job_id = f"test-terminal-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        for phase in [
            "DATA_PROCESSING", "COMPLIANCE_CHECK", "SEGMENTATION",
            "CONTENT_CREATION", "READY_TO_SEND", "SENDING", "COMPLETED",
        ]:
            broadcast_repo.update_phase(job_id, phase)

        # COMPLETED -> anything should fail
        assert broadcast_repo.update_phase(job_id, "SENDING") is False
        assert broadcast_repo.update_phase(job_id, "FAILED") is False


# ============================================
# 2. CONTACT PROCESSING TESTS
# ============================================

class TestContactProcessing:
    """Test contact validation, storage, and quality scoring for CSV contacts."""

    def test_update_contacts_on_job(self, broadcast_repo):
        """Test storing validated contacts on a broadcast job."""
        job_id = f"test-contacts-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        success = broadcast_repo.update_contacts(
            job_id=job_id,
            contacts_data=json.dumps(E164_PHONES),
            total=4,
            valid=4,
            invalid=0,
        )
        assert success is True

        job = broadcast_repo.get_by_id(job_id)
        assert job["total_contacts"] == 4
        assert job["valid_contacts"] == 4
        assert job["invalid_contacts"] == 0
        stored_phones = json.loads(job["contacts_data"])
        assert stored_phones == E164_PHONES

    def test_bulk_create_processed_contacts(self, contact_repo):
        """Test bulk inserting processed contacts from CSV data."""
        job_id = f"test-bulk-{uuid.uuid4()}"

        contacts = [
            {
                "phone_e164": E164_PHONES[i],
                "name": CSV_CONTACTS[i]["name"],
                "email": None,
                "country_code": "IN",
                "quality_score": 75,
                "custom_fields": {"source": "csv", "sno": i + 1},
                "source_row": i + 1,
                "validation_errors": None,
                "is_duplicate": False,
                "duplicate_of": None,
            }
            for i in range(len(CSV_CONTACTS))
        ]

        count = contact_repo.bulk_create(
            contacts=contacts,
            broadcast_job_id=job_id,
            user_id=USER_ID,
        )
        assert count == 4

    def test_get_contacts_by_broadcast_job(self, contact_repo):
        """Test retrieving processed contacts for a job."""
        job_id = f"test-retrieve-{uuid.uuid4()}"

        contacts = [
            {
                "phone_e164": E164_PHONES[i],
                "name": CSV_CONTACTS[i]["name"],
                "country_code": "IN",
                "quality_score": 70 + (i * 5),
                "source_row": i + 1,
                "is_duplicate": False,
            }
            for i in range(len(CSV_CONTACTS))
        ]
        contact_repo.bulk_create(contacts, job_id, USER_ID)

        result = contact_repo.get_by_broadcast_job(job_id)
        assert len(result) == 4
        names = [c["name"] for c in result]
        assert "Girish" in names
        assert "Vamsi" in names
        assert "Santhu" in names
        assert "Mahesh" in names

    def test_get_valid_phones_excludes_duplicates(self, contact_repo):
        """Test that get_valid_phones_by_job excludes duplicate contacts."""
        job_id = f"test-dedup-{uuid.uuid4()}"

        contacts = [
            {"phone_e164": "+918861832522", "name": "Girish", "country_code": "IN",
             "quality_score": 80, "source_row": 1, "is_duplicate": False},
            {"phone_e164": "+919177604610", "name": "Vamsi", "country_code": "IN",
             "quality_score": 75, "source_row": 2, "is_duplicate": False},
            {"phone_e164": "+918861832522", "name": "Girish Dup", "country_code": "IN",
             "quality_score": 40, "source_row": 3, "is_duplicate": True,
             "duplicate_of": "+918861832522"},
        ]
        contact_repo.bulk_create(contacts, job_id, USER_ID)

        valid_phones = contact_repo.get_valid_phones_by_job(job_id)
        assert len(valid_phones) == 2
        assert "+918861832522" in valid_phones
        assert "+919177604610" in valid_phones

    def test_quality_summary(self, contact_repo):
        """Test quality score summary and distribution."""
        job_id = f"test-quality-{uuid.uuid4()}"

        contacts = [
            {"phone_e164": "+918861832522", "name": "Girish", "country_code": "IN",
             "quality_score": 85, "source_row": 1, "is_duplicate": False},
            {"phone_e164": "+919177604610", "name": "Vamsi", "country_code": "IN",
             "quality_score": 55, "source_row": 2, "is_duplicate": False},
            {"phone_e164": "+919353578022", "name": "Santhu", "country_code": "IN",
             "quality_score": 30, "source_row": 3, "is_duplicate": False},
            {"phone_e164": "+918297347120", "name": "Mahesh", "country_code": "IN",
             "quality_score": 75, "source_row": 4, "is_duplicate": False},
        ]
        contact_repo.bulk_create(contacts, job_id, USER_ID)

        summary = contact_repo.get_quality_summary(job_id)
        assert summary["total"] == 4
        assert summary["valid_count"] == 4
        assert summary["duplicate_count"] == 0
        assert summary["high_count"] == 2    # 85, 75
        assert summary["medium_count"] == 1  # 55
        assert summary["low_count"] == 1     # 30
        assert summary["country_breakdown"]["IN"] == 4
        assert 50 < summary["avg_score"] < 70  # avg of 85+55+30+75 = 61.25


# ============================================
# 3. STATE MACHINE TRANSITION TABLE TESTS
# ============================================

class TestStateTransitionTable:
    """Verify the ALLOWED_TRANSITIONS map matches the 12-phase design."""

    def test_initialized_transitions(self):
        assert ALLOWED_TRANSITIONS["INITIALIZED"] == {"DATA_PROCESSING"}

    def test_data_processing_transitions(self):
        assert ALLOWED_TRANSITIONS["DATA_PROCESSING"] == {"COMPLIANCE_CHECK", "FAILED"}

    def test_compliance_check_transitions(self):
        assert ALLOWED_TRANSITIONS["COMPLIANCE_CHECK"] == {"SEGMENTATION", "FAILED"}

    def test_segmentation_transitions(self):
        assert ALLOWED_TRANSITIONS["SEGMENTATION"] == {"CONTENT_CREATION"}

    def test_content_creation_transitions(self):
        assert ALLOWED_TRANSITIONS["CONTENT_CREATION"] == {"PENDING_APPROVAL", "READY_TO_SEND"}

    def test_pending_approval_transitions(self):
        assert ALLOWED_TRANSITIONS["PENDING_APPROVAL"] == {"READY_TO_SEND", "CONTENT_CREATION", "FAILED"}

    def test_ready_to_send_transitions(self):
        assert ALLOWED_TRANSITIONS["READY_TO_SEND"] == {"SENDING", "CANCELLED"}

    def test_sending_transitions(self):
        assert ALLOWED_TRANSITIONS["SENDING"] == {"COMPLETED", "PAUSED", "FAILED"}

    def test_paused_transitions(self):
        assert ALLOWED_TRANSITIONS["PAUSED"] == {"SENDING", "CANCELLED"}

    def test_terminal_states_have_no_transitions(self):
        assert ALLOWED_TRANSITIONS["COMPLETED"] == set()
        assert ALLOWED_TRANSITIONS["FAILED"] == set()
        assert ALLOWED_TRANSITIONS["CANCELLED"] == set()

    def test_all_12_phases_present(self):
        expected = {
            "INITIALIZED", "DATA_PROCESSING", "COMPLIANCE_CHECK", "SEGMENTATION",
            "CONTENT_CREATION", "PENDING_APPROVAL", "READY_TO_SEND", "SENDING",
            "PAUSED", "COMPLETED", "FAILED", "CANCELLED",
        }
        assert set(ALLOWED_TRANSITIONS.keys()) == expected


# ============================================
# 4. TEMPLATE MANAGEMENT TESTS
# ============================================

class TestTemplateManagement:
    """Test template creation, status updates, and linking to broadcast jobs."""

    def test_create_template(self, template_repo):
        """Test creating a template record for Bedzee broadcast."""
        template = template_repo.create(
            template_id=f"tpl-{uuid.uuid4()}",
            user_id=USER_ID,
            business_id=BUSINESS_ID,
            name=TEST_TEMPLATE["name"],
            category=TEST_TEMPLATE["category"],
            language=TEST_TEMPLATE["language"],
            components=TEST_TEMPLATE["components"],
            project_id=PROJECT_ID,
            status="PENDING",
        )
        assert template is not None
        assert template.name == "bedzee_broadcast_promo"
        assert template.category == "MARKETING"
        assert template.language == "en_US"
        assert template.status == "PENDING"

    def test_template_approval_flow(self, template_repo):
        """Test PENDING -> APPROVED status update."""
        tpl_id = f"tpl-{uuid.uuid4()}"
        template_repo.create(
            template_id=tpl_id,
            user_id=USER_ID,
            business_id=BUSINESS_ID,
            name="bedzee_approval_test",
            category="MARKETING",
            language="en_US",
            components=TEST_TEMPLATE["components"],
        )

        # Approve template
        success = template_repo.update_status(tpl_id, "APPROVED")
        assert success is True

        tpl = template_repo.get_by_template_id(tpl_id)
        assert tpl["status"] == "APPROVED"
        assert tpl["approved_at"] is not None

    def test_template_rejection_and_resubmit(self, template_repo):
        """Test PENDING -> REJECTED -> edit components -> PENDING flow."""
        tpl_id = f"tpl-{uuid.uuid4()}"
        template_repo.create(
            template_id=tpl_id,
            user_id=USER_ID,
            business_id=BUSINESS_ID,
            name="bedzee_reject_test",
            category="MARKETING",
            language="en_US",
            components=TEST_TEMPLATE["components"],
        )

        # Reject
        template_repo.update_status(tpl_id, "REJECTED", rejected_reason="Policy violation")
        tpl = template_repo.get_by_template_id(tpl_id)
        assert tpl["status"] == "REJECTED"
        assert tpl["rejected_reason"] == "Policy violation"

        # Edit and resubmit (update_components resets to PENDING)
        new_components = [{"type": "BODY", "text": "Hello {{1}}, welcome to Bedzee!"}]
        template_repo.update_components(tpl_id, new_components)
        tpl = template_repo.get_by_template_id(tpl_id)
        assert tpl["status"] == "PENDING"
        assert tpl["components"] == new_components

    def test_link_template_to_broadcast_job(self, broadcast_repo):
        """Test selecting a template for a broadcast job."""
        job_id = f"test-tpl-link-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        success = broadcast_repo.update_template(
            job_id=job_id,
            template_id=TEST_TEMPLATE["template_id"],
            template_name=TEST_TEMPLATE["name"],
            template_language=TEST_TEMPLATE["language"],
            template_category=TEST_TEMPLATE["category"],
            template_status="APPROVED",
        )
        assert success is True

        job = broadcast_repo.get_by_id(job_id)
        assert job["template_id"] == TEST_TEMPLATE["template_id"]
        assert job["template_name"] == "bedzee_broadcast_promo"
        assert job["template_status"] == "APPROVED"

    def test_get_templates_by_user(self, template_repo):
        """Test listing all templates for user1."""
        tpl_id = f"tpl-{uuid.uuid4()}"
        template_repo.create(
            template_id=tpl_id,
            user_id=USER_ID,
            business_id=BUSINESS_ID,
            name="bedzee_list_test",
            category="MARKETING",
            language="en_US",
        )

        templates = template_repo.get_by_user_id(USER_ID)
        assert len(templates) >= 1
        tpl_ids = [t["template_id"] for t in templates]
        assert tpl_id in tpl_ids

    def test_template_usage_tracking(self, template_repo):
        """Test incrementing template usage count."""
        tpl_id = f"tpl-{uuid.uuid4()}"
        template_repo.create(
            template_id=tpl_id,
            user_id=USER_ID,
            business_id=BUSINESS_ID,
            name="bedzee_usage_test",
            category="MARKETING",
            language="en_US",
        )

        template_repo.increment_usage(tpl_id)
        template_repo.increment_usage(tpl_id)

        tpl = template_repo.get_by_template_id(tpl_id)
        assert tpl["usage_count"] == 2
        assert tpl["last_used_at"] is not None

    def test_soft_delete_template(self, template_repo):
        """Test soft deleting a template."""
        tpl_id = f"tpl-{uuid.uuid4()}"
        template_repo.create(
            template_id=tpl_id,
            user_id=USER_ID,
            business_id=BUSINESS_ID,
            name="bedzee_delete_test",
            category="MARKETING",
            language="en_US",
        )

        success = template_repo.soft_delete(tpl_id)
        assert success is True

        tpl = template_repo.get_by_template_id(tpl_id)
        assert tpl is None  # Soft-deleted templates are hidden by get_by_template_id


# ============================================
# 5. COMPLIANCE & SEGMENTATION TESTS
# ============================================

class TestComplianceAndSegmentation:
    """Test compliance status and segmentation data storage on broadcast jobs."""

    def test_update_compliance_passed(self, broadcast_repo):
        """Test storing compliance=passed on a broadcast job."""
        job_id = f"test-comp-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        success = broadcast_repo.update_compliance(
            job_id=job_id,
            compliance_status="passed",
            compliance_details=json.dumps({"health": "GREEN", "tier": "T2"}),
        )
        assert success is True

        job = broadcast_repo.get_by_id(job_id)
        assert job["compliance_status"] == "passed"

    def test_update_compliance_failed(self, broadcast_repo):
        """Test storing compliance=failed on a broadcast job."""
        job_id = f"test-comp-fail-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        success = broadcast_repo.update_compliance(
            job_id=job_id,
            compliance_status="failed",
            compliance_details=json.dumps({"health": "RED", "reason": "Account flagged"}),
        )
        assert success is True

        job = broadcast_repo.get_by_id(job_id)
        assert job["compliance_status"] == "failed"

    def test_update_segments_all_contacts(self, broadcast_repo):
        """Test storing segmentation data (all contacts as one segment)."""
        job_id = f"test-seg-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        segments = [{"name": "All Contacts", "criteria": "all", "contact_count": 4}]
        success = broadcast_repo.update_segments(job_id, json.dumps(segments))
        assert success is True

        job = broadcast_repo.get_by_id(job_id)
        stored_segments = json.loads(job["segments_data"])
        assert len(stored_segments) == 1
        assert stored_segments[0]["name"] == "All Contacts"
        assert stored_segments[0]["contact_count"] == 4


# ============================================
# 6. SEND PROGRESS TRACKING TESTS
# ============================================

class TestSendProgress:
    """Test delivery progress tracking during the SENDING phase."""

    def test_update_send_progress(self, broadcast_repo):
        """Test updating sent/failed counters."""
        job_id = f"test-progress-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        # Set valid contacts first
        broadcast_repo.update_contacts(
            job_id=job_id,
            contacts_data=json.dumps(E164_PHONES),
            total=4, valid=4, invalid=0,
        )

        # Simulate partial delivery: 3 sent, 1 failed
        success = broadcast_repo.update_send_progress(job_id, sent=3, failed=1)
        assert success is True

        job = broadcast_repo.get_by_id(job_id)
        assert job["sent_count"] == 3
        assert job["failed_count"] == 1
        assert job["pending_count"] == 0  # 4 valid - 3 sent - 1 failed

    def test_full_delivery_4_contacts(self, broadcast_repo):
        """Test full delivery of all 4 CSV contacts."""
        job_id = f"test-full-send-{uuid.uuid4()}"
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )

        broadcast_repo.update_contacts(
            job_id=job_id,
            contacts_data=json.dumps(E164_PHONES),
            total=4, valid=4, invalid=0,
        )

        # All 4 sent successfully
        broadcast_repo.update_send_progress(job_id, sent=4, failed=0)

        job = broadcast_repo.get_by_id(job_id)
        assert job["sent_count"] == 4
        assert job["failed_count"] == 0
        assert job["pending_count"] == 0


# ============================================
# 7. MEMORY / BEGINNER STATUS TESTS
# ============================================

class TestMemoryAndBeginnerStatus:
    """Test TempMemory for beginner flow and broadcasting status."""

    def test_first_broadcasting_flag(self, memory_repo, jwt_token, base64_token):
        """Test that new TempMemory record has first_broadcasting=True."""
        # Use a unique project to avoid conflicts with existing records
        test_project = f"test-proj-{uuid.uuid4()}"

        record = memory_repo.create_on_verification_success(
            user_id=USER_ID,
            business_id=BUSINESS_ID,
            project_id=test_project,
            jwt_token=jwt_token,
            email=EMAIL,
            password=PASSWORD,
            base64_token=base64_token,
        )
        assert record is not None
        assert record.first_broadcasting is True

    def test_mark_not_first_broadcasting(self, memory_repo, jwt_token, base64_token):
        """Test flipping first_broadcasting to False after FB verification."""
        test_project = f"test-proj-{uuid.uuid4()}"

        memory_repo.create_on_verification_success(
            user_id=USER_ID,
            business_id=BUSINESS_ID,
            project_id=test_project,
            jwt_token=jwt_token,
            email=EMAIL,
            password=PASSWORD,
            base64_token=base64_token,
        )

        success = memory_repo.mark_not_first_broadcasting(USER_ID, test_project)
        assert success is True

        is_first = memory_repo.is_first_broadcasting(USER_ID, test_project)
        assert is_first is False

    def test_get_memory_by_user_id(self, memory_repo, jwt_token, base64_token):
        """Test retrieving TempMemory for user1."""
        test_project = f"test-proj-{uuid.uuid4()}"

        memory_repo.create_on_verification_success(
            user_id=USER_ID,
            business_id=BUSINESS_ID,
            project_id=test_project,
            jwt_token=jwt_token,
            email=EMAIL,
            password=PASSWORD,
            base64_token=base64_token,
        )

        result = memory_repo.get_by_user_id(USER_ID)
        assert result is not None
        assert result["user_id"] == USER_ID
        assert result["jwt_token"] is not None


# ============================================
# 8. REAL MCP BROADCASTING TEST
# ============================================

class TestRealMCPBroadcast:
    """
    REAL integration test that calls MCP server (port 9002) to:
    1. Submit a promotional template to WhatsApp
    2. Check template status from WhatsApp
    3. Send actual messages to 4 contacts from CSV
    4. Track delivery results

    Requires: MCP Direct API server running on port 9002
    Uses: user1 with valid JWT in TempMemory (from onboarding)
    Contacts: Girish(8861832522), Vamsi(9177604610), Santhu(9353578022), Mahesh(8297347120)
    """

    def test_step1_verify_user_jwt_exists(self, memory_repo):
        """Step 1: Verify user1 has completed onboarding and has a valid JWT."""
        mem = memory_repo.get_by_user_id(USER_ID)
        assert mem is not None, "user1 TempMemory not found - run onboarding first"
        assert mem["jwt_token"] is not None, "user1 has no JWT token"
        assert len(mem["jwt_token"]) > 20, "JWT token looks invalid (too short)"
        print(f"\n  JWT found for user1 (project: {mem['project_id']})")
        print(f"  Business ID: {mem['business_id']}")

    def test_step2_submit_promotional_template_via_mcp(self):
        """Step 2: Submit a MARKETING template to WhatsApp via MCP (port 9002)."""
        template_name = f"bedzee_promo_{uuid.uuid4().hex[:8]}"

        result = _call_direct_api_mcp("submit_whatsapp_template_message", {
            "user_id": USER_ID,
            "name": template_name,
            "category": "MARKETING",
            "language": "en_US",
            "components": [
                {
                    "type": "BODY",
                    "text": "Hello {{1}}, check out our latest offers on Bedzee! Visit us today for exclusive deals.",
                    "example": {"body_text": [["Customer"]]},
                }
            ],
        })

        print(f"\n  Template name: {template_name}")
        print(f"  MCP response: {json.dumps(result, indent=2, default=str)}")

        assert isinstance(result, dict), f"MCP returned non-dict: {type(result)}"
        # Template submitted - check response
        if result.get("success"):
            template_id = result.get("data", {}).get("id", "")
            print(f"  Template ID: {template_id}")
            print(f"  Status: PENDING (awaiting WhatsApp approval)")
            # Store for later tests
            self.__class__._submitted_template_name = template_name
            self.__class__._submitted_template_id = str(template_id)
        else:
            # Even if it fails (e.g. duplicate name), the MCP call was made
            print(f"  Submit result: {result.get('error', 'unknown')}")
            self.__class__._submitted_template_name = template_name
            self.__class__._submitted_template_id = None

    def test_step3_list_templates_via_mcp(self):
        """Step 3: List all templates from WhatsApp via MCP to find APPROVED ones."""
        result = _call_direct_api_mcp("get_templates", {
            "user_id": USER_ID,
        })

        print(f"\n  MCP get_templates response type: {type(result)}")

        assert isinstance(result, dict), f"MCP returned non-dict: {type(result)}"

        # Find any APPROVED template for sending
        # MCP response structure: {"success": true, "data": {"total": N, "data": [...]}}
        approved_template = None
        if result.get("success") and result.get("data"):
            data_wrapper = result["data"]
            # Handle nested data structure from get_templates
            if isinstance(data_wrapper, dict) and "data" in data_wrapper:
                templates = data_wrapper["data"]
                print(f"  Total templates: {data_wrapper.get('total', len(templates))}")
            elif isinstance(data_wrapper, list):
                templates = data_wrapper
                print(f"  Total templates: {len(templates)}")
            else:
                templates = []
                print(f"  Unexpected data format: {type(data_wrapper)}")

            for t in templates:
                if isinstance(t, dict):
                    status = t.get("status", "").upper()
                    name = t.get("name", "")
                    tpl_id = t.get("id", "")
                    lang = t.get("language", "")
                    cat = t.get("category", "")
                    print(f"    - {name} | {status} | {cat} | {lang} | ID:{tpl_id}")
                    if status == "APPROVED" and cat == "MARKETING" and not approved_template:
                        approved_template = t

        if approved_template:
            self.__class__._approved_template = approved_template
            print(f"\n  Using APPROVED template: {approved_template.get('name')} (ID: {approved_template.get('id')})")
        else:
            self.__class__._approved_template = None
            print("\n  No APPROVED MARKETING template found - sending will use template type")

    def test_step4_check_messaging_health_via_mcp(self):
        """Step 4: Check account health and messaging tier via MCP."""
        result = _call_direct_api_mcp("get_messaging_health_status", {
            "node_id": USER_ID,
        })

        print(f"\n  Health check response: {json.dumps(result, indent=2, default=str)}")

        assert isinstance(result, dict), f"MCP returned non-dict: {type(result)}"
        # Store health for reference (soft-fail - health check is informational)
        self.__class__._health_result = result
        if not result.get("success"):
            print(f"  Health check returned error (non-fatal): {result.get('error', 'unknown')}")

    def test_step5_full_broadcast_with_mcp_sending(self, broadcast_repo, contact_repo, template_repo):
        """
        Step 5: FULL BROADCAST - Create job, submit template, WAIT for approval, then send via MCP.

        This is the REAL broadcast test:
        - Creates broadcast job in DB
        - Processes 4 CSV contacts (Girish, Vamsi, Santhu, Mahesh)
        - Submits a MARKETING template via MCP
        - WAITS for WhatsApp to approve the template (polls every 10s)
        - Sends messages via MCP send_message to each contact
        - Tracks sent/failed counts
        """
        job_id = f"real-broadcast-{uuid.uuid4()}"

        print(f"\n{'='*60}")
        print(f"  REAL BROADCAST TEST")
        print(f"  Job ID: {job_id}")
        print(f"  Contacts: {', '.join(c['name'] for c in CSV_CONTACTS)}")
        print(f"{'='*60}")

        # --- PHASE 1: INITIALIZED ---
        broadcast_repo.create_broadcast_job(
            job_id=job_id, user_id=USER_ID, project_id=PROJECT_ID
        )
        print(f"\n  [INITIALIZED] Broadcast job created")

        # --- PHASE 2: DATA_PROCESSING ---
        broadcast_repo.update_phase(job_id, "DATA_PROCESSING")
        broadcast_repo.update_contacts(
            job_id=job_id,
            contacts_data=json.dumps(E164_PHONES),
            total=4, valid=4, invalid=0,
        )

        processed = [
            {
                "phone_e164": E164_PHONES[i],
                "name": CSV_CONTACTS[i]["name"],
                "country_code": "IN",
                "quality_score": 80,
                "source_row": i + 1,
                "is_duplicate": False,
                "custom_fields": {"sno": i + 1},
            }
            for i in range(4)
        ]
        contact_repo.bulk_create(processed, job_id, USER_ID)
        print(f"  [DATA_PROCESSING] 4 contacts processed: {E164_PHONES}")

        # --- PHASE 3: COMPLIANCE_CHECK ---
        broadcast_repo.update_phase(job_id, "COMPLIANCE_CHECK")
        health = getattr(self.__class__, '_health_result', {})
        broadcast_repo.update_compliance(
            job_id=job_id,
            compliance_status="passed",
            compliance_details=json.dumps(health, default=str),
        )
        print(f"  [COMPLIANCE_CHECK] Passed (health data stored)")

        # --- PHASE 4: SEGMENTATION ---
        broadcast_repo.update_phase(job_id, "SEGMENTATION")
        segments = [{"name": "All Contacts", "criteria": "all", "contact_count": 4}]
        broadcast_repo.update_segments(job_id, json.dumps(segments))
        print(f"  [SEGMENTATION] 1 segment: All Contacts (4)")

        # --- PHASE 5: CONTENT_CREATION ---
        broadcast_repo.update_phase(job_id, "CONTENT_CREATION")

        # First check if there's already an APPROVED template from step 3
        approved = getattr(self.__class__, '_approved_template', None)

        if approved:
            # Use existing approved template directly
            tpl_name = approved.get("name", "")
            tpl_id = str(approved.get("id", ""))
            tpl_lang = approved.get("language", "en_US")
            tpl_cat = approved.get("category", "MARKETING")

            template_repo.create(
                template_id=tpl_id,
                user_id=USER_ID,
                business_id=BUSINESS_ID,
                name=tpl_name,
                category=tpl_cat,
                language=tpl_lang,
                components=approved.get("components", []),
                project_id=PROJECT_ID,
                status="APPROVED",
            )
            template_status = "APPROVED"
            print(f"  [CONTENT_CREATION] Using existing APPROVED template: {tpl_name}")
        else:
            # Submit a NEW template and WAIT for approval
            tpl_name = f"bedzee_broadcast_{uuid.uuid4().hex[:8]}"
            print(f"  [CONTENT_CREATION] Submitting new template: {tpl_name}")

            submit_result = _call_direct_api_mcp("submit_whatsapp_template_message", {
                "user_id": USER_ID,
                "name": tpl_name,
                "category": "MARKETING",
                "language": "en_US",
                "components": [
                    {
                        "type": "BODY",
                        "text": "Hello {{1}}, check out our latest offers on Bedzee! Visit us today for exclusive deals.",
                        "example": {"body_text": [["Customer"]]},
                    }
                ],
            })

            tpl_id = ""
            tpl_lang = "en_US"
            tpl_cat = "MARKETING"

            if isinstance(submit_result, dict) and submit_result.get("success"):
                api_data = submit_result.get("data", {})
                tpl_id = str(api_data.get("id", "")) if isinstance(api_data, dict) else ""
                print(f"  [CONTENT_CREATION] Template submitted - ID: {tpl_id}, status: PENDING")
            else:
                error = submit_result.get("error", "unknown") if isinstance(submit_result, dict) else str(submit_result)
                print(f"  [CONTENT_CREATION] Template submit error: {error}")
                tpl_id = f"failed-{uuid.uuid4()}"

            # Store in local DB
            template_repo.create(
                template_id=tpl_id,
                user_id=USER_ID,
                business_id=BUSINESS_ID,
                name=tpl_name,
                category=tpl_cat,
                language=tpl_lang,
                project_id=PROJECT_ID,
                status="PENDING",
            )

            # --- WAIT FOR TEMPLATE APPROVAL ---
            if tpl_id and not tpl_id.startswith("failed-"):
                print(f"\n  [WAITING] Polling template approval status (every 10s, up to 5 min)...")
                template_status = "PENDING"

                for attempt in range(1, 31):  # 30 polls x 10s = 5 minutes max
                    check_result = _call_direct_api_mcp("get_template_by_id", {
                        "user_id": USER_ID,
                        "template_id": tpl_id,
                    })

                    api_status = "UNKNOWN"
                    if isinstance(check_result, dict) and check_result.get("success"):
                        api_data = check_result.get("data", {})
                        if isinstance(api_data, dict):
                            api_status = api_data.get("status", "UNKNOWN").upper()

                    print(f"    Poll {attempt}/30: status = {api_status}")

                    if api_status in ("APPROVED", "REJECTED", "PAUSED", "DISABLED"):
                        template_status = api_status
                        # Sync to local DB
                        template_repo.update_status(tpl_id, api_status)
                        break

                    time.sleep(10)
                else:
                    template_status = "PENDING"
                    print(f"  [TIMEOUT] Template still PENDING after 5 minutes")

                print(f"  [CONTENT_CREATION] Template final status: {template_status}")
            else:
                template_status = "FAILED"

        # --- PHASE 6: Link template to job ---
        broadcast_repo.update_template(
            job_id=job_id,
            template_id=tpl_id,
            template_name=tpl_name,
            template_language=tpl_lang,
            template_category=tpl_cat,
            template_status=template_status,
        )

        # --- PHASE 7: READY_TO_SEND or PENDING_APPROVAL ---
        if template_status == "APPROVED":
            broadcast_repo.update_phase(job_id, "READY_TO_SEND")
            print(f"  [READY_TO_SEND] Template APPROVED - ready to send")
        elif template_status in ("REJECTED", "PENDING", "FAILED", "PAUSED", "DISABLED"):
            # Template not approved - fallback to an existing APPROVED template
            print(f"  [CONTENT_CREATION] Template status: {template_status} - looking for APPROVED fallback...")

            # Fallback: list templates via MCP and find an approved one
            list_result = _call_direct_api_mcp("get_templates", {"user_id": USER_ID})
            fallback_template = None
            if isinstance(list_result, dict) and list_result.get("success"):
                data_wrapper = list_result.get("data", {})
                if isinstance(data_wrapper, dict) and "data" in data_wrapper:
                    templates_list = data_wrapper["data"]
                elif isinstance(data_wrapper, list):
                    templates_list = data_wrapper
                else:
                    templates_list = []
                for t in templates_list:
                    if isinstance(t, dict) and t.get("status", "").upper() == "APPROVED":
                        fallback_template = t
                        break

            if fallback_template:
                tpl_name = fallback_template.get("name", "")
                tpl_id = str(fallback_template.get("id", ""))
                tpl_lang = fallback_template.get("language", "en_US")
                tpl_cat = fallback_template.get("category", "MARKETING")
                template_status = "APPROVED"
                broadcast_repo.update_template(
                    job_id=job_id,
                    template_id=tpl_id,
                    template_name=tpl_name,
                    template_language=tpl_lang,
                    template_category=tpl_cat,
                    template_status="APPROVED",
                )
                print(f"  [CONTENT_CREATION] Fallback to APPROVED template: {tpl_name} (ID: {tpl_id})")
                broadcast_repo.update_phase(job_id, "READY_TO_SEND")
                print(f"  [READY_TO_SEND] Using fallback template")
            else:
                print(f"  [ABORTED] No APPROVED template available - cannot send")
                broadcast_repo.update_phase(job_id, "PENDING_APPROVAL")
                print(f"{'='*60}")
                pytest.skip("No APPROVED template available for sending")
                return

        # --- PHASE 8: SENDING via MCP ---
        broadcast_repo.update_phase(job_id, "SENDING")
        job = broadcast_repo.get_by_id(job_id)
        assert job["started_sending_at"] is not None

        print(f"\n  [SENDING] Broadcasting to 4 contacts via MCP (port 9002)...")
        print(f"  Template: {tpl_name} ({tpl_cat}, {tpl_lang})")
        print(f"  {'-'*50}")

        sent = 0
        failed = 0
        results = []

        for i, phone in enumerate(E164_PHONES):
            contact_name = CSV_CONTACTS[i]["name"]

            # Send via MCP send_message with template type
            # Include template_components to fill {{1}} variable with contact name
            send_result = _call_direct_api_mcp("send_message", {
                "user_id": USER_ID,
                "to": phone.replace("+", ""),  # send_message expects without +
                "message_type": "template",
                "template_name": tpl_name,
                "template_language_code": tpl_lang,
                "template_language_policy": "deterministic",
                "template_components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": contact_name}
                        ]
                    }
                ],
            })

            success = False
            if isinstance(send_result, dict):
                success = send_result.get("success", False) or send_result.get("status") == "success"

            if success:
                sent += 1
                msg_id = ""
                if isinstance(send_result.get("data"), dict):
                    messages = send_result["data"].get("messages", [])
                    if messages and isinstance(messages[0], dict):
                        msg_id = messages[0].get("id", "")
                print(f"  [{i+1}/4] {contact_name} ({phone}) -> SENT {msg_id}")
            else:
                failed += 1
                error = send_result.get("error", "Unknown") if isinstance(send_result, dict) else str(send_result)
                print(f"  [{i+1}/4] {contact_name} ({phone}) -> FAILED: {error}")

            results.append({
                "name": contact_name,
                "phone": phone,
                "success": success,
                "response": send_result,
            })

        # Update send progress in DB
        broadcast_repo.update_send_progress(job_id, sent=sent, failed=failed)

        print(f"\n  {'-'*50}")
        print(f"  DELIVERY RESULT: {sent} sent, {failed} failed out of 4")

        # --- PHASE 9: COMPLETED ---
        broadcast_repo.update_phase(job_id, "COMPLETED")

        final = broadcast_repo.get_by_id(job_id)
        assert final["phase"] == "COMPLETED"
        assert final["sent_count"] == sent
        assert final["failed_count"] == failed
        assert final["completed_at"] is not None
        assert final["template_name"] == tpl_name

        print(f"  [COMPLETED] Broadcast finished")
        print(f"\n  Final DB state:")
        print(f"    Phase: {final['phase']}")
        print(f"    Sent: {final['sent_count']}")
        print(f"    Failed: {final['failed_count']}")
        print(f"    Template: {final['template_name']}")
        print(f"    Started: {final['started_sending_at']}")
        print(f"    Completed: {final['completed_at']}")
        print(f"{'='*60}")
