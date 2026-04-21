from api.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE alerts DROP CONSTRAINT IF EXISTS chk_alert_feedback"))
    conn.execute(text("ALTER TABLE alerts ADD CONSTRAINT chk_alert_feedback CHECK (feedback IN ('pending', 'approved', 'false_positive', 'auto_resolved'))"))
    conn.commit()
    print("Constraint updated successfully! auto_resolved is now a valid feedback value.")
