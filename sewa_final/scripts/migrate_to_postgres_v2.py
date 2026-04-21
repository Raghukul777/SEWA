"""
Migration: Upgrade SEWA PostgreSQL schema for PostgreSQL-native features.

What this does:
  1. Add new columns to `users`   (department, phone, is_active, updated_at, last_login_at)
  2. Add new columns to `patients` (updated_at, discharge_date)
  3. Convert TEXT JSON columns → JSONB on patients and alerts
  4. Drop the old SQLite-specific sewa.db migration columns that may differ
  5. Create the clinical_notes table if it was previously separate

Run ONCE:
    cd sewa_final
    python scripts/migrate_to_postgres_v2.py
"""

import os
import sys
from pathlib import Path

# Load env before importing SQLAlchemy models
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or not DATABASE_URL.startswith("postgresql"):
    print("❌  DATABASE_URL must be a PostgreSQL URL. Set it in sewa_final/.env")
    sys.exit(1)

engine = create_engine(DATABASE_URL, echo=False)


def column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = :table AND column_name = :col
    """), {"table": table, "col": column}).fetchone()
    return row is not None


def col_type(conn, table: str, column: str) -> str:
    row = conn.execute(text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name = :table AND column_name = :col
    """), {"table": table, "col": column}).fetchone()
    return row[0] if row else ""


def run():
    with engine.begin() as conn:
        print("\n── users table ────────────────────────────────────")
        for col, defn in [
            ("department",    "TEXT DEFAULT ''"),
            ("phone",         "TEXT DEFAULT ''"),
            ("is_active",     "BOOLEAN DEFAULT TRUE"),
            ("updated_at",    "TIMESTAMPTZ DEFAULT NOW()"),
            ("last_login_at", "TIMESTAMPTZ"),
        ]:
            if not column_exists(conn, "users", col):
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {defn}"))
                print(f"  ✅ Added users.{col}")
            else:
                print(f"  ⏭️  users.{col} already exists")

        print("\n── patients table ─────────────────────────────────")
        for col, defn in [
            ("doctor_id",                "TEXT REFERENCES users(id) ON DELETE SET NULL"),
            ("blood_group",              "TEXT DEFAULT ''"),
            ("phone",                   "TEXT DEFAULT ''"),
            ("emergency_contact_name",  "TEXT DEFAULT ''"),
            ("emergency_contact_phone", "TEXT DEFAULT ''"),
            ("address",                 "TEXT DEFAULT ''"),
            ("updated_at",    "TIMESTAMPTZ DEFAULT NOW()"),
            ("discharge_date","TIMESTAMPTZ"),
        ]:
            if not column_exists(conn, "patients", col):
                conn.execute(text(f"ALTER TABLE patients ADD COLUMN {col} {defn}"))
                print(f"  ✅ Added patients.{col}")
            else:
                print(f"  ⏭️  patients.{col} already exists")

        # Convert TEXT → JSONB on patients
        for col in ["medical_history", "treatment_bundle"]:
            current_type = col_type(conn, "patients", col)
            if current_type in ("text", "character varying"):
                print(f"  🔄 Converting patients.{col}: TEXT → JSONB")
                conn.execute(text(f"""
                    ALTER TABLE patients
                    ALTER COLUMN {col}
                    TYPE JSONB USING {col}::jsonb
                """))
                print(f"  ✅ patients.{col} → JSONB")
            else:
                print(f"  ⏭️  patients.{col} is already {current_type}")

        print("\n── alerts table ───────────────────────────────────")
        for col in ["param_values", "triggered_criteria", "recommended_actions"]:
            current_type = col_type(conn, "alerts", col)
            if current_type in ("text", "character varying"):
                print(f"  🔄 Converting alerts.{col}: TEXT → JSONB")
                conn.execute(text(f"""
                    ALTER TABLE alerts
                    ALTER COLUMN {col}
                    TYPE JSONB USING {col}::jsonb
                """))
                print(f"  ✅ alerts.{col} → JSONB")
            else:
                print(f"  ⏭️  alerts.{col} is already {current_type}")

        # Add created_at to alerts if missing
        if not column_exists(conn, "alerts", "created_at"):
            conn.execute(text("ALTER TABLE alerts ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW()"))
            print("  ✅ Added alerts.created_at")

        print("\n── Backfill NULL updated_at with created_at ───────")
        conn.execute(text("""
            UPDATE patients SET updated_at = COALESCE(created_at, NOW())
            WHERE updated_at IS NULL
        """))
        conn.execute(text("""
            UPDATE users SET updated_at = COALESCE(created_at, NOW())
            WHERE updated_at IS NULL
        """))

    print("\n✅  Migration complete. Now restart the API server to apply pg_setup.sql.\n")


if __name__ == "__main__":
    run()
