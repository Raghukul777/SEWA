"""
SEWA Database Models and Session Setup
PostgreSQL via SQLAlchemy 2.x.

Key PostgreSQL features used:
  - JSONB  for medical_history, treatment_bundle, param_values, etc.
  - Triggers (defined in pg_setup.sql): auto-updated_at, audit-on-discharge,
    alert suppression check, patient-status change audit
  - Materialized & regular Views: active_patients_summary (fast dashboard load)
  - Indexes: partial, composite, GIN (for JSONB)
  - Check constraints: valid risk levels, severity, feedback, gender
  - Sequences / UUIDs: gen_random_uuid() for alert IDs
"""

import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean,
    DateTime, Text, ForeignKey, event, text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ── Database location ───────────────────────────────────────────────
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sewa")

# ── Engine ──────────────────────────────────────────────────────────
# PostgreSQL-specific: connection pool tuning, server-side cursors ready
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,        # detect stale connections
    pool_recycle=3600,         # recycle connections every hour
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Models ──────────────────────────────────────────────────────────

class User(Base):
    """
    Registered doctors / administrators.
    Each doctor owns their own set of patients.
    """
    __tablename__ = "users"

    id               = Column(String, primary_key=True, index=True)   # e.g. "D-1001"
    email            = Column(String, unique=True, index=True, nullable=False)
    hashed_password  = Column(String, nullable=False)
    name             = Column(String, nullable=False)
    hospital_name    = Column(String, default="")
    department       = Column(String, default="")          # e.g. ICU, Emergency
    phone            = Column(String, default="")
    role             = Column(String, default="Doctor")    # Doctor | Administrator | Nurse
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow)
    last_login_at    = Column(DateTime, nullable=True)


class Patient(Base):
    """
    ICU patients managed by a specific doctor.
    Uses JSONB for flexible clinical data fields.
    """
    __tablename__ = "patients"

    patient_id               = Column(String, primary_key=True, index=True)
    doctor_id                = Column(String, ForeignKey("users.id", ondelete="SET NULL"),
                                      index=True, nullable=True)

    # Demographics
    name                     = Column(String, nullable=False)
    age                      = Column(Integer)
    gender                   = Column(String)              # Male | Female | Other
    blood_group              = Column(String, default="")  # A+ | B- | O+ etc.

    # Contact details
    phone                    = Column(String, default="")
    address                  = Column(Text, default="")
    emergency_contact_name   = Column(String, default="")
    emergency_contact_phone  = Column(String, default="")

    # Admission info
    bed_number               = Column(String)
    admission_reason         = Column(String)
    admission_date           = Column(DateTime, default=datetime.utcnow)
    discharge_date           = Column(DateTime, nullable=True)

    # Clinical classification
    trajectory               = Column(String, default="stable")
    # stable | early_sepsis | rapid_deterioration

    # JSONB fields — efficient querying/filtering on keys
    medical_history          = Column(JSONB, default=list)
    # ["Diabetes", "Hypertension", ...]

    treatment_bundle         = Column(JSONB, default=dict)
    # {"lactate_measure": false, "antibiotics": true, ...}

    # Synthetic data source mapping
    synthetic_data_id        = Column(Integer, nullable=True, index=True)
    # Links to patient ID in synthetic_patients.csv for vitals streaming

    data_sync_started_at     = Column(DateTime, nullable=True)
    # When the synthetic data stream started for this patient

    data_sync_ended_at       = Column(DateTime, nullable=True)
    # When the synthetic data stream ended (e.g., on discharge)

    # Status tracking
    status                   = Column(String, default="Stable")
    # Stable | Warning | Critical
    is_active                = Column(Boolean, default=True)

    # Metadata
    created_at               = Column(DateTime, default=datetime.utcnow)
    updated_at               = Column(DateTime, default=datetime.utcnow)


class VitalReading(Base):
    """
    Time-series vital sign recordings per patient.
    Indexed heavily on (patient_id, timestamp DESC) for trend queries.
    """
    __tablename__ = "vital_readings"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    patient_id       = Column(String, ForeignKey("patients.patient_id", ondelete="CASCADE"),
                              index=True, nullable=False)
    timestamp        = Column(DateTime, default=datetime.utcnow, index=True)

    # Haemodynamic
    heart_rate       = Column(Float)
    spo2             = Column(Float)
    sbp              = Column(Float)    # Systolic BP
    dbp              = Column(Float)    # Diastolic BP
    map              = Column(Float)    # Mean Arterial Pressure

    # Respiratory
    temperature      = Column(Float)
    respiratory_rate = Column(Float)

    # Laboratory
    lactate          = Column(Float)
    wbc              = Column(Float)
    creatinine       = Column(Float)


class Alert(Base):
    """
    Sepsis risk alerts, one per event.
    param_values, triggered_criteria, recommended_actions stored as JSONB
    for direct querying (e.g. filter alerts where lactate > 4).
    """
    __tablename__ = "alerts"

    id                   = Column(String, primary_key=True, index=True)   # UUID
    patient_id           = Column(String, ForeignKey("patients.patient_id", ondelete="CASCADE"),
                                  index=True, nullable=False)
    timestamp            = Column(DateTime, default=datetime.utcnow)

    risk_level           = Column(String)          # LOW | MODERATE | HIGH | CRITICAL
    clinical_summary     = Column(Text, default="")

    # JSONB — enables direct querying on vital values inside alerts
    param_values         = Column(JSONB, default=dict)
    triggered_criteria   = Column(JSONB, default=list)
    recommended_actions  = Column(JSONB, default=list)

    feedback             = Column(String, default="pending")
    # pending | approved | false_positive
    is_active            = Column(Boolean, default=True)
    created_at           = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """
    Immutable audit trail. Rows are NEVER updated or deleted.
    PostgreSQL trigger ensures audit entries cascade automatically
    for certain patient/alert state changes.
    """
    __tablename__ = "audit_logs"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    timestamp         = Column(DateTime, default=datetime.utcnow, index=True)
    event_type        = Column(String, index=True)
    severity          = Column(String)             # info | warning | critical
    patient_id        = Column(String, nullable=True, index=True)
    patient_name      = Column(String, nullable=True)
    user_email        = Column(String, default="system")
    event_description = Column(Text)


class ClinicalNote(Base):
    """
    Clinical notes written by doctors for a patient.
    """
    __tablename__ = "clinical_notes"

    id         = Column(String, primary_key=True)   # UUID
    patient_id = Column(String, ForeignKey("patients.patient_id", ondelete="CASCADE"),
                         index=True, nullable=False)
    text       = Column(Text, nullable=False)
    author     = Column(String, default="Unknown")
    timestamp  = Column(DateTime, default=datetime.utcnow)


# ── Helpers ─────────────────────────────────────────────────────────

def create_tables():
    """Create all tables if they don't exist yet (idempotent)."""
    Base.metadata.create_all(bind=engine)


def apply_pg_setup(pg_sql_path: Path):
    """
    Execute the PostgreSQL setup script (triggers, indexes, views, functions).
    Called once at startup. Uses IF NOT EXISTS / CREATE OR REPLACE — safe to re-run.

    Each statement runs in its own transaction so one warning doesn't
    abort the entire script (important for EXISTS guards).
    """
    if not pg_sql_path.exists():
        print(f"⚠️  pg_setup.sql not found at {pg_sql_path}, skipping.")
        return

    raw = pg_sql_path.read_text(encoding="utf-8")
    statements = _split_sql(raw)

    ok = 0
    warn = 0
    # AUTOCOMMIT: each statement is its own transaction — failures are isolated
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for stmt in statements:
            stripped = stmt.strip()
            if not stripped:
                continue
            # Only skip statements that are PURELY comments (all non-blank lines start with --)
            non_comment_lines = [
                l for l in stripped.splitlines()
                if l.strip() and not l.strip().startswith("--")
            ]
            if not non_comment_lines:
                continue   # pure comment block — skip
            # Execute the SQL (psycopg2 handles leading SQL comments fine)
            sql_to_execute = "\n".join(non_comment_lines)
            try:
                conn.execute(text(sql_to_execute))
                ok += 1
            except Exception as e:
                msg = str(e).split("\n")[0][:160]
                # Ignore "already exists" / harmless idempotency warnings
                if any(x in msg for x in ("already exists", "does not exist", "duplicate")):
                    pass
                else:
                    print(f"⚠️  pg_setup: {msg}")
                warn += 1

    print(f"✅  PostgreSQL setup applied ({ok} ok, {warn} skipped).")


def _split_sql(sql: str) -> list:
    """
    Split a SQL script into individual statements.
    Handles dollar-quoted PL/pgSQL bodies ($$...$$) correctly.
    """
    statements = []
    current = []
    in_dollar_block = False

    for line in sql.splitlines():
        stripped = line.strip()

        # Toggle dollar-quote blocks
        if "$$" in stripped:
            count = stripped.count("$$")
            if count % 2 == 1:           # odd number of $$ → toggles the block
                in_dollar_block = not in_dollar_block

        current.append(line)

        # Only split on ; when NOT inside a dollar-quoted block
        if not in_dollar_block and stripped.endswith(";"):
            statements.append("\n".join(current))
            current = []

    if current:
        tail = "\n".join(current).strip()
        if tail:
            statements.append(tail)

    return statements


def get_db():
    """FastAPI dependency: yields a DB session and ensures it's closed."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
