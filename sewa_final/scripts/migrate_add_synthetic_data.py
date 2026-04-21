"""
Migration script to add synthetic data tracking columns to patients table.
Run this once to update the database schema.
"""

import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.database import engine
from sqlalchemy import text


def migrate():
    """Add synthetic_data_id and sync timestamps to patients table."""

    with engine.begin() as conn:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='patients' AND column_name='synthetic_data_id'
        """)).first()

        if result:
            print("✅  synthetic_data_id column already exists. Skipping migration.")
            return

        print("Adding synthetic data tracking columns to patients table...")

        # Add the new columns
        conn.execute(text("""
            ALTER TABLE patients 
            ADD COLUMN synthetic_data_id INTEGER,
            ADD COLUMN data_sync_started_at TIMESTAMP,
            ADD COLUMN data_sync_ended_at TIMESTAMP
        """))

        # Create index on synthetic_data_id for faster lookups
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_patients_synthetic_data_id 
            ON patients(synthetic_data_id)
        """))

        print("✅  Migration completed successfully!")
        print("   - Added synthetic_data_id column")
        print("   - Added data_sync_started_at column")
        print("   - Added data_sync_ended_at column")
        print("   - Created index on synthetic_data_id")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌  Migration failed: {e}")
        sys.exit(1)

