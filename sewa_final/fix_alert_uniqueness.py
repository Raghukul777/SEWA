"""
Apply DB-level unique partial index to enforce: only 1 active+pending alert per patient.
This is the only race-condition-proof solution.
"""
from api.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # First, clean up existing duplicate active alerts — keep only the latest per patient
    conn.execute(text("""
        DELETE FROM alerts
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY patient_id
                           ORDER BY timestamp DESC
                       ) AS rn
                FROM alerts
                WHERE is_active = TRUE AND feedback = 'pending'
            ) ranked
            WHERE rn > 1
        )
    """))
    print("Cleaned up duplicate active alerts.")

    # Add the unique partial index — only 1 active+pending alert allowed per patient
    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_alert_per_patient
        ON alerts (patient_id)
        WHERE is_active = TRUE AND feedback = 'pending'
    """))
    conn.commit()
    print("Unique partial index created: idx_one_active_alert_per_patient")
    print("PostgreSQL will now physically reject duplicate active alerts per patient.")
