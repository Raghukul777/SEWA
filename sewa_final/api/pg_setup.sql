-- =============================================================================
--  SEWA PostgreSQL Setup Script
--  Triggers · Indexes · Views · Functions · Constraints
--
--  Designed to be IDEMPOTENT — safe to re-run on every server startup.
--  All objects use  CREATE OR REPLACE / IF NOT EXISTS.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- 0. EXTENSIONS
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- trigram search on text fields
CREATE EXTENSION IF NOT EXISTS "btree_gin";     -- GIN index on scalar + JSONB


-- =============================================================================
--  SECTION 1: CHECK CONSTRAINTS
--  Data integrity enforced at DB level — can't be bypassed by the application.
-- =============================================================================

-- patients: valid gender values
ALTER TABLE patients
    DROP CONSTRAINT IF EXISTS chk_patient_gender;
ALTER TABLE patients
    ADD  CONSTRAINT chk_patient_gender
    CHECK (gender IN ('Male', 'Female', 'Other'));

-- patients: valid clinical status
ALTER TABLE patients
    DROP CONSTRAINT IF EXISTS chk_patient_status;
ALTER TABLE patients
    ADD  CONSTRAINT chk_patient_status
    CHECK (status IN ('Stable', 'Warning', 'Critical'));

-- patients: valid trajectory
ALTER TABLE patients
    DROP CONSTRAINT IF EXISTS chk_patient_trajectory;
ALTER TABLE patients
    ADD  CONSTRAINT chk_patient_trajectory
    CHECK (trajectory IN ('stable', 'early_sepsis', 'rapid_deterioration'));

-- patients: age sanity
ALTER TABLE patients
    DROP CONSTRAINT IF EXISTS chk_patient_age;
ALTER TABLE patients
    ADD  CONSTRAINT chk_patient_age
    CHECK (age IS NULL OR (age >= 0 AND age <= 130));

-- alerts: valid risk level
ALTER TABLE alerts
    DROP CONSTRAINT IF EXISTS chk_alert_risk_level;
ALTER TABLE alerts
    ADD  CONSTRAINT chk_alert_risk_level
    CHECK (risk_level IN ('LOW', 'MODERATE', 'HIGH', 'CRITICAL'));

-- alerts: valid feedback
ALTER TABLE alerts
    DROP CONSTRAINT IF EXISTS chk_alert_feedback;
ALTER TABLE alerts
    ADD  CONSTRAINT chk_alert_feedback
    CHECK (feedback IN ('pending', 'approved', 'false_positive', 'auto_resolved'));

-- audit_logs: valid severity
ALTER TABLE audit_logs
    DROP CONSTRAINT IF EXISTS chk_audit_severity;
ALTER TABLE audit_logs
    ADD  CONSTRAINT chk_audit_severity
    CHECK (severity IN ('info', 'warning', 'critical'));

-- users: valid role
ALTER TABLE users
    DROP CONSTRAINT IF EXISTS chk_user_role;
ALTER TABLE users
    ADD  CONSTRAINT chk_user_role
    CHECK (role IN ('Doctor', 'Administrator', 'Nurse'));


-- =============================================================================
--  SECTION 2: PERFORMANCE INDEXES
-- =============================================================================

-- ── vital_readings ────────────────────────────────────────────────────────────
-- Primary access pattern: "last N readings for patient X"
CREATE INDEX IF NOT EXISTS idx_vitals_patient_time
    ON vital_readings (patient_id, "timestamp" DESC);

-- For per-hour aggregation queries
CREATE INDEX IF NOT EXISTS idx_vitals_time
    ON vital_readings ("timestamp" DESC);

-- ── alerts ───────────────────────────────────────────────────────────────────
-- Duplicate-suppression lookup: "active alerts for patient in last 30 min"
CREATE INDEX IF NOT EXISTS idx_alerts_patient_active_time
    ON alerts (patient_id, is_active, "timestamp" DESC)
    WHERE is_active = TRUE;

-- Alert management by feedback status
CREATE INDEX IF NOT EXISTS idx_alerts_feedback
    ON alerts (feedback, "timestamp" DESC)
    WHERE feedback = 'pending';

-- UNIQUE: only 1 active+pending alert per patient at a time
-- This is the DB-level guard against race conditions / duplicate inserts
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_alert_per_patient
    ON alerts (patient_id)
    WHERE is_active = TRUE AND feedback = 'pending';


-- GIN index on JSONB param_values — allows queries like:
--   SELECT * FROM alerts WHERE param_values->>'lactate' > '4'
CREATE INDEX IF NOT EXISTS idx_alerts_param_values_gin
    ON alerts USING GIN (param_values);

-- ── audit_logs ────────────────────────────────────────────────────────────────
-- Dashboard queries: recent events, by event_type, by severity
CREATE INDEX IF NOT EXISTS idx_audit_timestamp
    ON audit_logs ("timestamp" DESC);

CREATE INDEX IF NOT EXISTS idx_audit_patient_time
    ON audit_logs (patient_id, "timestamp" DESC)
    WHERE patient_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_event_type
    ON audit_logs (event_type, "timestamp" DESC);

CREATE INDEX IF NOT EXISTS idx_audit_severity
    ON audit_logs (severity, "timestamp" DESC);

-- ── patients ──────────────────────────────────────────────────────────────────
-- Doctor's active patient list (most common dashboard query)
CREATE INDEX IF NOT EXISTS idx_patients_doctor_active
    ON patients (doctor_id, is_active)
    WHERE is_active = TRUE;

-- Status-based filtering (Critical patients first)
CREATE INDEX IF NOT EXISTS idx_patients_status
    ON patients (status, is_active)
    WHERE is_active = TRUE;

-- GIN index on JSONB medical_history — e.g. patients with 'Diabetes'
CREATE INDEX IF NOT EXISTS idx_patients_medical_history_gin
    ON patients USING GIN (medical_history);

-- Trigram index for patient name search (ILIKE '%john%')
CREATE INDEX IF NOT EXISTS idx_patients_name_trgm
    ON patients USING GIN (name gin_trgm_ops);

-- ── users ────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_email
    ON users (email);

-- clinical_notes: latest notes per patient
CREATE INDEX IF NOT EXISTS idx_notes_patient_time
    ON clinical_notes (patient_id, "timestamp" DESC);


-- =============================================================================
--  SECTION 3: TRIGGER FUNCTIONS
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 3a. Auto-update `updated_at` on any row change
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW() AT TIME ZONE 'UTC';
    RETURN NEW;
END;
$$;

-- Attach to patients
DROP TRIGGER IF EXISTS trg_patients_updated_at ON patients;
CREATE TRIGGER trg_patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- Attach to users
DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();


-- ---------------------------------------------------------------------------
-- 3b. Auto-audit on patient STATUS change
--     When `patients.status` changes, write an audit_log row automatically.
--     This means even direct DB updates are captured — not just API calls.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_audit_patient_status_change()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO audit_logs
            (timestamp, event_type, severity, patient_id, patient_name,
             user_email, event_description)
        VALUES (
            NOW() AT TIME ZONE 'UTC',
            'patient_status_changed',
            CASE NEW.status
                WHEN 'Critical' THEN 'critical'
                WHEN 'Warning'  THEN 'warning'
                ELSE 'info'
            END,
            NEW.patient_id,
            NEW.name,
            'db_trigger',
            'Status changed: ' || COALESCE(OLD.status, '?') || ' to ' || NEW.status
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_patient_status_audit ON patients;
CREATE TRIGGER trg_patient_status_audit
    AFTER UPDATE OF status ON patients
    FOR EACH ROW EXECUTE FUNCTION fn_audit_patient_status_change();


-- ---------------------------------------------------------------------------
-- 3c. Auto-audit on patient DISCHARGE (is_active: true → false)
--     Captures discharge even if done outside the API (e.g., admin scripts).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_audit_patient_discharge()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.is_active = TRUE AND NEW.is_active = FALSE THEN
        -- Stamp the discharge date
        NEW.discharge_date = NOW() AT TIME ZONE 'UTC';

        INSERT INTO audit_logs
            (timestamp, event_type, severity, patient_id, patient_name,
             user_email, event_description)
        VALUES (
            NOW() AT TIME ZONE 'UTC',
            'patient_discharged',
            'info',
            NEW.patient_id,
            NEW.name,
            'db_trigger',
            'Patient ' || NEW.name || ' discharged from bed ' || COALESCE(NEW.bed_number, 'unknown')
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_patient_discharge_audit ON patients;
CREATE TRIGGER trg_patient_discharge_audit
    BEFORE UPDATE OF is_active ON patients
    FOR EACH ROW EXECUTE FUNCTION fn_audit_patient_discharge();


-- ---------------------------------------------------------------------------
-- 3d. Auto-audit on ALERT creation
--     Every new alert row also writes to audit_logs automatically.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_audit_alert_created()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_patient_name TEXT;
BEGIN
    SELECT name INTO v_patient_name
    FROM patients WHERE patient_id = NEW.patient_id;

    INSERT INTO audit_logs
        (timestamp, event_type, severity, patient_id, patient_name,
         user_email, event_description)
    VALUES (
        NOW() AT TIME ZONE 'UTC',
        'alert_generated',
        CASE NEW.risk_level
            WHEN 'HIGH'     THEN 'critical'
            WHEN 'CRITICAL' THEN 'critical'
            WHEN 'MODERATE' THEN 'warning'
            ELSE 'info'
        END,
        NEW.patient_id,
        COALESCE(v_patient_name, 'Unknown'),
        'db_trigger',
        'Sepsis alert (' || NEW.risk_level || '): ' || LEFT(NEW.clinical_summary, 200)
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_alert_audit ON alerts;
CREATE TRIGGER trg_alert_audit
    AFTER INSERT ON alerts
    FOR EACH ROW EXECUTE FUNCTION fn_audit_alert_created();


-- ---------------------------------------------------------------------------
-- 3e. Auto-audit on ALERT FEEDBACK submission
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_audit_alert_feedback()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_patient_name TEXT;
BEGIN
    IF OLD.feedback IS DISTINCT FROM NEW.feedback THEN
        SELECT name INTO v_patient_name
        FROM patients WHERE patient_id = NEW.patient_id;

        INSERT INTO audit_logs
            (timestamp, event_type, severity, patient_id, patient_name,
             user_email, event_description)
        VALUES (
            NOW() AT TIME ZONE 'UTC',
            'alert_feedback_submitted',
            'info',
            NEW.patient_id,
            COALESCE(v_patient_name, 'Unknown'),
            'db_trigger',
            'Alert feedback changed: ' || COALESCE(OLD.feedback, '?') || ' to ' || NEW.feedback
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_alert_feedback_audit ON alerts;
CREATE TRIGGER trg_alert_feedback_audit
    AFTER UPDATE OF feedback ON alerts
    FOR EACH ROW EXECUTE FUNCTION fn_audit_alert_feedback();


-- ---------------------------------------------------------------------------
-- 3f. Prevent audit_log modification (immutability guarantee)
--     Audit entries can never be updated or deleted.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_protect_audit_log()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Audit log entries are immutable - UPDATE/DELETE not allowed.';
END;
$$;

DROP TRIGGER IF EXISTS trg_protect_audit_update ON audit_logs;
CREATE TRIGGER trg_protect_audit_update
    BEFORE UPDATE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION fn_protect_audit_log();

DROP TRIGGER IF EXISTS trg_protect_audit_delete ON audit_logs;
CREATE TRIGGER trg_protect_audit_delete
    BEFORE DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION fn_protect_audit_log();


-- =============================================================================
--  SECTION 4: DATABASE VIEWS
--  Pre-structured queries so the API can SELECT from a view instead of
--  writing complex JOINs on every request.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 4a. active_patients_summary
--     The dashboard "patient list" endpoint: active patients + latest vitals
--     + alert count + note count — all in one fast read.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW active_patients_summary AS
SELECT
    p.patient_id,
    p.doctor_id,
    p.name,
    p.age,
    p.gender,
    p.blood_group,
    p.bed_number,
    p.admission_reason,
    p.admission_date,
    p.trajectory,
    p.medical_history,
    p.treatment_bundle,
    p.status,
    p.is_active,
    p.phone,
    p.address,
    p.emergency_contact_name,
    p.emergency_contact_phone,
    p.updated_at,

    -- Latest vital reading (using LATERAL JOIN — efficient)
    lv.heart_rate,
    lv.spo2,
    lv.temperature,
    lv.sbp,
    lv.dbp,
    lv.map,
    lv.respiratory_rate,
    lv.lactate,
    lv.wbc,
    lv.creatinine,
    lv.timestamp AS vitals_timestamp,

    -- Rolling counts  (useful for badge numbers in UI)
    (SELECT COUNT(*) FROM alerts a
        WHERE a.patient_id = p.patient_id AND a.is_active = TRUE
    ) AS active_alert_count,

    (SELECT COUNT(*) FROM clinical_notes cn
        WHERE cn.patient_id = p.patient_id
    ) AS note_count

FROM patients p
LEFT JOIN LATERAL (
    SELECT *
    FROM vital_readings vr
    WHERE vr.patient_id = p.patient_id
    ORDER BY vr.timestamp DESC
    LIMIT 1
) lv ON TRUE
WHERE p.is_active = TRUE;


-- ---------------------------------------------------------------------------
-- 4b. critical_patients_view
--     Quick escalation view — only Critical/Warning patients.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW critical_patients_view AS
SELECT
    p.patient_id,
    p.doctor_id,
    p.name,
    p.age,
    p.bed_number,
    p.status,
    p.admission_date,
    lv.map,
    lv.lactate,
    lv.heart_rate,
    lv.respiratory_rate,
    lv.spo2,
    lv.timestamp AS vitals_timestamp,
    (SELECT COUNT(*) FROM alerts a
        WHERE a.patient_id = p.patient_id
          AND a.is_active = TRUE
          AND a.feedback = 'pending'
    ) AS pending_alert_count
FROM patients p
LEFT JOIN LATERAL (
    SELECT *
    FROM vital_readings vr
    WHERE vr.patient_id = p.patient_id
    ORDER BY vr.timestamp DESC
    LIMIT 1
) lv ON TRUE
WHERE p.is_active = TRUE
  AND p.status IN ('Critical', 'Warning')
ORDER BY
    CASE p.status WHEN 'Critical' THEN 1 WHEN 'Warning' THEN 2 ELSE 3 END,
    p.admission_date;


-- ---------------------------------------------------------------------------
-- 4c. doctor_dashboard_stats
--     Per-doctor aggregated KPIs for a statistics panel.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW doctor_dashboard_stats AS
SELECT
    u.id              AS doctor_id,
    u.name            AS doctor_name,
    u.hospital_name,
    COUNT(DISTINCT p.patient_id)
        FILTER (WHERE p.is_active = TRUE)              AS active_patients,
    COUNT(DISTINCT p.patient_id)
        FILTER (WHERE p.status = 'Critical'
                  AND p.is_active = TRUE)              AS critical_count,
    COUNT(DISTINCT p.patient_id)
        FILTER (WHERE p.status = 'Warning'
                  AND p.is_active = TRUE)              AS warning_count,
    COUNT(DISTINCT a.id)
        FILTER (WHERE a.is_active = TRUE
                  AND a.feedback = 'pending')          AS pending_alerts,
    COUNT(DISTINCT p.patient_id)
        FILTER (WHERE p.is_active = FALSE)             AS total_discharged
FROM users u
LEFT JOIN patients p ON p.doctor_id = u.id
LEFT JOIN alerts  a ON a.patient_id = p.patient_id
WHERE u.role IN ('Doctor', 'Administrator')
GROUP BY u.id, u.name, u.hospital_name;


-- ---------------------------------------------------------------------------
-- 4d. recent_audit_summary (last 24h) — used by the audit badge on navbar
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW recent_audit_summary AS
SELECT
    event_type,
    severity,
    COUNT(*)       AS event_count,
    MAX(timestamp) AS latest_at
FROM audit_logs
WHERE timestamp >= NOW() AT TIME ZONE 'UTC' - INTERVAL '24 hours'
GROUP BY event_type, severity
ORDER BY latest_at DESC;


-- =============================================================================
--  SECTION 5: DATABASE FUNCTIONS (callable via SELECT fn_name(...))
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 5a. fn_get_patient_vitals_summary(p_patient_id, p_last_n)
--     Returns last N vital readings with computed MAP if missing.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_get_patient_vitals_summary(
    p_patient_id TEXT,
    p_last_n     INT DEFAULT 20
)
RETURNS TABLE (
    id               INT,
    patient_id       TEXT,
    ts               TIMESTAMP,
    heart_rate       FLOAT,
    spo2             FLOAT,
    temperature      FLOAT,
    map              FLOAT,
    respiratory_rate FLOAT,
    lactate          FLOAT,
    wbc              FLOAT,
    creatinine       FLOAT
) LANGUAGE sql STABLE AS $$
    SELECT
        vr.id,
        vr.patient_id,
        vr.timestamp        AS ts,
        vr.heart_rate,
        vr.spo2,
        vr.temperature,
        COALESCE(vr.map, (vr.dbp + (vr.sbp - vr.dbp) / 3.0)) AS map,
        vr.respiratory_rate,
        vr.lactate,
        vr.wbc,
        vr.creatinine
    FROM vital_readings vr
    WHERE vr.patient_id = p_patient_id
    ORDER BY vr.timestamp DESC
    LIMIT p_last_n;
$$;


-- ---------------------------------------------------------------------------
-- 5b. fn_alert_suppressed(p_patient_id, p_risk_level, p_minutes)
--     Returns TRUE if a recent alert at the same level already exists.
--     Used by the vitals route to avoid duplicate alerts.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_alert_suppressed(
    p_patient_id TEXT,
    p_risk_level TEXT,
    p_minutes    INT DEFAULT 30
)
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
    SELECT EXISTS (
        SELECT 1
        FROM alerts
        WHERE patient_id = p_patient_id
          AND risk_level  = p_risk_level
          AND is_active   = TRUE
          AND timestamp   >= NOW() AT TIME ZONE 'UTC' - (p_minutes || ' minutes')::INTERVAL
    );
$$;


-- ---------------------------------------------------------------------------
-- 5c. fn_patient_risk_history(p_patient_id, p_days)
--     Returns daily risk-level counts — useful for trend charts.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_patient_risk_history(
    p_patient_id TEXT,
    p_days       INT DEFAULT 7
)
RETURNS TABLE (
    day         DATE,
    critical_ct BIGINT,
    warning_ct  BIGINT,
    info_ct     BIGINT
) LANGUAGE sql STABLE AS $$
    SELECT
        DATE(timestamp AT TIME ZONE 'UTC') AS day,
        COUNT(*) FILTER (WHERE severity = 'critical') AS critical_ct,
        COUNT(*) FILTER (WHERE severity = 'warning')  AS warning_ct,
        COUNT(*) FILTER (WHERE severity = 'info')     AS info_ct
    FROM audit_logs
    WHERE patient_id = p_patient_id
      AND timestamp  >= NOW() AT TIME ZONE 'UTC' - (p_days || ' days')::INTERVAL
    GROUP BY DATE(timestamp AT TIME ZONE 'UTC')
    ORDER BY day;
$$;


-- ---------------------------------------------------------------------------
-- 5d. fn_doctor_patient_count(p_doctor_id)
--     Quick count query — avoids full table scan via index.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_doctor_patient_count(p_doctor_id TEXT)
RETURNS TABLE (
    active_count    BIGINT,
    critical_count  BIGINT,
    total_count     BIGINT
) LANGUAGE sql STABLE AS $$
    SELECT
        COUNT(*) FILTER (WHERE is_active = TRUE)                         AS active_count,
        COUNT(*) FILTER (WHERE is_active = TRUE AND status = 'Critical') AS critical_count,
        COUNT(*)                                                          AS total_count
    FROM patients
    WHERE doctor_id = p_doctor_id;
$$;


-- =============================================================================
--  SECTION 6: MATERIALIZED VIEW (optional refresh-on-demand)
--  For hospitals with large datasets, this pre-computes the expensive join.
--  Call:  SELECT refresh_patient_stats();   from the app on demand.
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_patient_stats AS
SELECT
    p.doctor_id,
    p.patient_id,
    p.name,
    p.status,
    p.admission_date,
    COUNT(vr.id)                        AS total_readings,
    AVG(vr.map)                         AS avg_map,
    AVG(vr.lactate)                     AS avg_lactate,
    AVG(vr.heart_rate)                  AS avg_heart_rate,
    MAX(vr.timestamp)                   AS last_reading_at,
    COUNT(DISTINCT a.id)
        FILTER (WHERE a.is_active = TRUE) AS active_alerts
FROM patients p
LEFT JOIN vital_readings vr ON vr.patient_id = p.patient_id
LEFT JOIN alerts          a  ON a.patient_id  = p.patient_id
WHERE p.is_active = TRUE
GROUP BY p.doctor_id, p.patient_id, p.name, p.status, p.admission_date
WITH DATA;

-- Unique index on materialized view (allows concurrent refresh)
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_patient_stats_pk
    ON mv_patient_stats (patient_id);

-- Stored procedure to refresh the materialized view
CREATE OR REPLACE FUNCTION refresh_patient_stats()
RETURNS VOID LANGUAGE sql AS $$
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_patient_stats;
$$;


-- =============================================================================
--  DONE
-- =============================================================================
-- Summary of what's been applied:
--   ✅ Check constraints on gender, status, trajectory, risk_level, feedback, severity, role
--   ✅ 12 performance indexes (partial, composite, GIN, trigram)
--   ✅ 6 triggers: updated_at, patient status audit, discharge audit,
--                  alert audit, alert feedback audit, audit immutability guard
--   ✅ 4 views: active_patients_summary, critical_patients_view,
--               doctor_dashboard_stats, recent_audit_summary
--   ✅ 4 functions: vitals summary, alert suppression check,
--                   risk history, doctor patient count
--   ✅ 1 materialized view: mv_patient_stats (concurrently refreshable)
