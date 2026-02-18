-- Legal Drafting Agent - Complete Database Schema
-- PostgreSQL 14+
-- Court-Grade Multi-Agent System

-- ============================================================================
-- EXTENSIONS REQUIRED
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- TABLE 1: DRAFTING SESSIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS drafting_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'completed', 'failed')),
    current_step INTEGER DEFAULT 0,
    workflow_state JSONB,
    final_output JSONB,
    error_log JSONB DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_user_sessions
ON drafting_sessions (user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_session_status
ON drafting_sessions (status);

CREATE INDEX IF NOT EXISTS idx_session_step
ON drafting_sessions (current_step);

-- ============================================================================
-- TABLE 2: MASTER FACTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS master_facts (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES drafting_sessions(session_id) ON DELETE CASCADE,
    fact_type VARCHAR(100) DEFAULT 'general',
    fact_content JSONB NOT NULL,
    source_doc_id VARCHAR(255),
    confidence_score DECIMAL(3,2)
        CHECK (confidence_score >= 0 AND confidence_score <= 1),
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_facts
ON master_facts (session_id);

CREATE INDEX IF NOT EXISTS idx_verified_facts
ON master_facts (verified, session_id);

CREATE INDEX IF NOT EXISTS idx_confidence_score
ON master_facts (confidence_score);

-- ============================================================================
-- TABLE 3: AGENT OUTPUTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_outputs (
    output_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES drafting_sessions(session_id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    agent_output JSONB NOT NULL,
    execution_time_ms INTEGER,
    model_used VARCHAR(100),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_outputs
ON agent_outputs (session_id, step_number);

CREATE INDEX IF NOT EXISTS idx_agent_performance
ON agent_outputs (agent_name, execution_time_ms);

CREATE INDEX IF NOT EXISTS idx_failed_outputs
ON agent_outputs (success, agent_name);

-- ============================================================================
-- TABLE 4: VALIDATION REPORTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS validation_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES drafting_sessions(session_id) ON DELETE CASCADE,
    gate_name VARCHAR(100) NOT NULL,
    validation_result JSONB NOT NULL,
    hard_blocks JSONB DEFAULT '[]'::jsonb,
    passed BOOLEAN NOT NULL,
    stop_triggered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_validations
ON validation_reports (session_id);

CREATE INDEX IF NOT EXISTS idx_failed_validations
ON validation_reports (passed, gate_name);

CREATE INDEX IF NOT EXISTS idx_stopped_validations
ON validation_reports (stop_triggered);

-- ============================================================================
-- TABLE 5: VERIFIED CITATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS verified_citations (
    citation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citation_text TEXT NOT NULL,
    case_name VARCHAR(500) NOT NULL,
    year INTEGER CHECK (year >= 1800 AND year <= 2100),
    court VARCHAR(200),
    holding TEXT,
    citation_hash VARCHAR(64) UNIQUE NOT NULL,
    source_db VARCHAR(100),
    source_url TEXT,
    verified_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_citation_hash
ON verified_citations (citation_hash);

CREATE INDEX IF NOT EXISTS idx_case_name
ON verified_citations (case_name);

CREATE INDEX IF NOT EXISTS idx_year
ON verified_citations (year);

CREATE INDEX IF NOT EXISTS idx_court
ON verified_citations (court);

-- ============================================================================
-- TABLE 6: DRAFT VERSIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS draft_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES drafting_sessions(session_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    draft_content TEXT NOT NULL,
    quality_score DECIMAL(5,2)
        CHECK (quality_score >= 0 AND quality_score <= 100),
    court_readiness VARCHAR(50)
        CHECK (court_readiness IN ('READY', 'NEEDS_REVIEW', 'BLOCKED')),
    generated_by VARCHAR(100),
    word_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (session_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_session_versions
ON draft_versions (session_id, version_number);

CREATE INDEX IF NOT EXISTS idx_quality_score
ON draft_versions (quality_score);

-- ============================================================================
-- TABLE 7: MISTAKE RULES MAIN (PRODUCTION DB)
-- ============================================================================
CREATE TABLE IF NOT EXISTS mistake_rules_main (
    rule_id VARCHAR(50) PRIMARY KEY,
    doc_type VARCHAR(200) NOT NULL,
    court_type VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    rule_type VARCHAR(100) NOT NULL CHECK (rule_type IN (
        'mandatory_section', 'formatting', 'annexure', 'prayer',
        'verification', 'limitation', 'jurisdiction', 'valuation', 'court_fee'
    )),
    instruction TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    frequency_count INTEGER DEFAULT 0,
    last_seen DATE,
    active BOOLEAN DEFAULT TRUE,
    promoted_from_staging BOOLEAN DEFAULT FALSE,
    promoted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_doc_lookup
ON mistake_rules_main (doc_type, court_type, state);

CREATE INDEX IF NOT EXISTS idx_severity
ON mistake_rules_main (severity, active);

CREATE INDEX IF NOT EXISTS idx_rule_type
ON mistake_rules_main (rule_type);

CREATE INDEX IF NOT EXISTS idx_frequency
ON mistake_rules_main (frequency_count DESC);

CREATE INDEX IF NOT EXISTS idx_active_rules
ON mistake_rules_main (active, doc_type, court_type, state);

-- ============================================================================
-- TABLE 8: STAGING RULES (CANDIDATE DB)
-- ============================================================================
CREATE TABLE IF NOT EXISTS staging_rules (
    staging_rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL,
    session_id UUID REFERENCES drafting_sessions(session_id),
    doc_type VARCHAR(200) NOT NULL,
    court_type VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    rule_type VARCHAR(100) NOT NULL,
    instruction TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    promoted BOOLEAN DEFAULT FALSE,
    promoted_at TIMESTAMP,
    main_rule_id VARCHAR(50) REFERENCES mistake_rules_main(rule_id),
    first_seen TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_lookup
ON staging_rules (doc_type, court_type, state, instruction);

CREATE INDEX IF NOT EXISTS idx_promotion_candidates
ON staging_rules (promoted, severity);

CREATE INDEX IF NOT EXISTS idx_case_rules
ON staging_rules (case_id);

CREATE INDEX IF NOT EXISTS idx_not_promoted
ON staging_rules (promoted)
WHERE promoted = FALSE;

-- ============================================================================
-- TABLE 9: PROMOTION LOGS (AUDIT DB)
-- ============================================================================
CREATE TABLE IF NOT EXISTS promotion_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    promotion_id UUID NOT NULL,
    doc_type VARCHAR(200) NOT NULL,
    court_type VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    promoted_rules JSONB NOT NULL,
    rejected_rules JSONB DEFAULT '[]'::jsonb,
    promotion_criteria JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_promotion_history
ON promotion_logs (doc_type, court_type, state, created_at);

CREATE INDEX IF NOT EXISTS idx_promotion_id
ON promotion_logs (promotion_id);

-- ============================================================================
-- TABLE 10: CLARIFICATION HISTORY
-- ============================================================================
CREATE TABLE IF NOT EXISTS clarification_history (
    clarification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES drafting_sessions(session_id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    questions JSONB NOT NULL,
    user_responses JSONB,
    asked_at TIMESTAMP DEFAULT NOW(),
    responded_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_session_clarifications
ON clarification_history (session_id);

CREATE INDEX IF NOT EXISTS idx_pending_clarifications
ON clarification_history (responded_at)
WHERE responded_at IS NULL;

-- ============================================================================
-- TABLE 11: UPLOADED DOCUMENTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS uploaded_documents (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES drafting_sessions(session_id) ON DELETE CASCADE,
    file_name VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER,
    mime_type VARCHAR(100),
    doc_text TEXT,
    extracted_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_docs
ON uploaded_documents (session_id);

-- ============================================================================
-- TABLE 12: EXPORT HISTORY
-- ============================================================================
CREATE TABLE IF NOT EXISTS export_history (
    export_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES drafting_sessions(session_id) ON DELETE CASCADE,
    draft_version_id UUID REFERENCES draft_versions(version_id),
    export_format VARCHAR(10) CHECK (export_format IN ('docx', 'pdf')),
    file_path TEXT,
    exported_at TIMESTAMP DEFAULT NOW(),
    downloaded BOOLEAN DEFAULT FALSE,
    downloaded_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_session_exports
ON export_history (session_id);

CREATE INDEX IF NOT EXISTS idx_export_format
ON export_history (export_format);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Promotion candidates (rules that appear in 3+ cases)
CREATE OR REPLACE VIEW promotion_candidates AS
SELECT
    instruction,
    doc_type,
    court_type,
    state,
    rule_type,
    severity,
    COUNT(DISTINCT case_id) AS occurrence_count,
    MIN(first_seen) AS first_occurrence,
    MAX(first_seen) AS last_occurrence
FROM staging_rules
WHERE promoted = FALSE
  AND severity IN ('medium', 'high')
GROUP BY instruction, doc_type, court_type, state, rule_type, severity
HAVING COUNT(DISTINCT case_id) >= 3;

-- View: Active sessions with step progress
CREATE OR REPLACE VIEW active_session_progress AS
SELECT
    s.session_id,
    s.user_id,
    s.current_step,
    s.status,
    s.created_at,
    COUNT(DISTINCT ao.step_number) AS completed_steps,
    MAX(ao.created_at) AS last_activity
FROM drafting_sessions s
LEFT JOIN agent_outputs ao ON s.session_id = ao.session_id
WHERE s.status = 'active'
GROUP BY s.session_id, s.user_id, s.current_step, s.status, s.created_at;

-- View: Quality scores by document type
CREATE OR REPLACE VIEW quality_by_doc_type AS
SELECT
    s.workflow_state->>'doc_type' AS doc_type,
    COUNT(*) AS total_drafts,
    AVG(dv.quality_score) AS avg_quality_score,
    MIN(dv.quality_score) AS min_quality_score,
    MAX(dv.quality_score) AS max_quality_score,
    COUNT(CASE WHEN dv.court_readiness = 'READY' THEN 1 END) AS ready_count
FROM draft_versions dv
JOIN drafting_sessions s ON dv.session_id = s.session_id
WHERE dv.quality_score IS NOT NULL
GROUP BY s.workflow_state->>'doc_type';

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: Update session timestamp on changes
CREATE OR REPLACE FUNCTION update_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update session timestamp
DROP TRIGGER IF EXISTS trigger_update_session_timestamp ON drafting_sessions;
CREATE TRIGGER trigger_update_session_timestamp
    BEFORE UPDATE ON drafting_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_timestamp();

-- Function: Increment rule frequency
CREATE OR REPLACE FUNCTION increment_rule_frequency(p_rule_ids VARCHAR[])
RETURNS VOID AS $$
BEGIN
    UPDATE mistake_rules_main
    SET frequency_count = frequency_count + 1,
        last_seen = CURRENT_DATE
    WHERE rule_id = ANY(p_rule_ids);
END;
$$ LANGUAGE plpgsql;

-- Function: Promote staging rule
CREATE OR REPLACE FUNCTION promote_staging_rule(
    p_instruction TEXT,
    p_doc_type VARCHAR,
    p_court_type VARCHAR,
    p_state VARCHAR,
    p_rule_type VARCHAR,
    p_severity VARCHAR,
    p_occurrence_count INTEGER
)
RETURNS VARCHAR AS $$
DECLARE
    v_rule_id VARCHAR;
    v_next_id INTEGER;
BEGIN
    SELECT COALESCE(MAX(CAST(SUBSTRING(rule_id FROM 2) AS INTEGER)), 0) + 1
    INTO v_next_id
    FROM mistake_rules_main;

    v_rule_id := 'R' || LPAD(v_next_id::TEXT, 3, '0');

    INSERT INTO mistake_rules_main (
        rule_id, doc_type, court_type, state, rule_type,
        instruction, severity, frequency_count, promoted_from_staging
    ) VALUES (
        v_rule_id, p_doc_type, p_court_type, p_state, p_rule_type,
        p_instruction, p_severity, p_occurrence_count, TRUE
    );

    UPDATE staging_rules
    SET promoted = TRUE,
        promoted_at = NOW(),
        main_rule_id = v_rule_id
    WHERE doc_type = p_doc_type
      AND court_type = p_court_type
      AND state = p_state
      AND instruction = p_instruction
      AND promoted = FALSE;

    RETURN v_rule_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SEED DATA
-- ============================================================================

INSERT INTO mistake_rules_main (
    rule_id, doc_type, court_type, state, rule_type,
    instruction, severity, frequency_count
) VALUES
('R001', 'Bail Application', 'Sessions', 'Karnataka', 'mandatory_section',
 'Always cite Section 439 CrPC in bail applications before Sessions Court',
 'high', 47),

('R002', 'Bail Application', 'Sessions', 'Karnataka', 'annexure',
 'Attach copy of FIR as Annexure A',
 'high', 52),

('R003', 'Writ Petition', 'HighCourt', 'Karnataka', 'mandatory_section',
 'Cite Article 226 of the Constitution in the title',
 'high', 89),

('R004', 'Appeal', 'HighCourt', 'Karnataka', 'limitation',
 'Appeal must be filed within 90 days from order date',
 'high', 34),

('R005', 'Complaint u/s 138 NI Act', 'Magistrate', 'Karnataka', 'mandatory_section',
 'State that notice was sent within 30 days of cheque dishonor',
 'high', 28)
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO verified_citations (
    case_name, citation_text, year, court, holding, citation_hash
) VALUES
('Sanjay Chandra vs. CBI', '(2011) 12 SCC 530', 2011, 'Supreme Court',
 'Bail is the rule, jail is the exception', 'a1b2c3d4e5f6'),

('State of Rajasthan vs. Balchand', '(1977) 4 SCC 308', 1977, 'Supreme Court',
 'Purpose of bail is to secure attendance of accused at trial', 'f6e5d4c3b2a1'),

('Gudikanti Narasimhulu vs. Public Prosecutor', '1978 AIR 429', 1978, 'Supreme Court',
 'Bail should not be refused as a form of punishment', 'a9b8c7d6e5f4')
ON CONFLICT (citation_hash) DO NOTHING;

-- ============================================================================
-- PERFORMANCE OPTIMIZATION
-- ============================================================================
ANALYZE drafting_sessions;
ANALYZE master_facts;
ANALYZE agent_outputs;
ANALYZE validation_reports;
ANALYZE verified_citations;
ANALYZE draft_versions;
ANALYZE mistake_rules_main;
ANALYZE staging_rules;
ANALYZE promotion_logs;
ANALYZE clarification_history;
ANALYZE uploaded_documents;
ANALYZE export_history;

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE drafting_sessions IS 'Main session tracking for document drafting workflow';
COMMENT ON TABLE master_facts IS 'Extracted facts with source attribution and confidence scores';
COMMENT ON TABLE agent_outputs IS 'Output from each agent execution for audit trail';
COMMENT ON TABLE validation_reports IS 'Reports from validation gates (Steps 3, 10)';
COMMENT ON TABLE verified_citations IS 'Hash-verified legal citations from trusted sources';
COMMENT ON TABLE draft_versions IS 'Version history of generated drafts';
COMMENT ON TABLE mistake_rules_main IS 'Production database of verified mistake rules';
COMMENT ON TABLE staging_rules IS 'Candidate rules awaiting promotion (3+ occurrences)';
COMMENT ON TABLE promotion_logs IS 'Audit trail of rule promotions from staging to main';
COMMENT ON TABLE clarification_history IS 'User clarification questions and responses';
COMMENT ON TABLE uploaded_documents IS 'User-uploaded documents for fact extraction';
COMMENT ON TABLE export_history IS 'History of document exports (DOCX/PDF)';
