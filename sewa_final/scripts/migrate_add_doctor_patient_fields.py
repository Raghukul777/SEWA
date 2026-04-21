"""
Migration script: Add doctor_id + extended patient fields to existing sewa.db
Run once: python scripts/migrate_add_doctor_patient_fields.py
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "sewa.db"

COLUMNS_TO_ADD = [
    ("doctor_id",               "TEXT"),
    ("phone",                   "TEXT DEFAULT ''"),
    ("blood_group",             "TEXT DEFAULT ''"),
    ("emergency_contact_name",  "TEXT DEFAULT ''"),
    ("emergency_contact_phone", "TEXT DEFAULT ''"),
    ("address",                 "TEXT DEFAULT ''"),
]

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def run():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. It will be created fresh on next startup.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    added = []
    for col_name, col_def in COLUMNS_TO_ADD:
        if not column_exists(cur, "patients", col_name):
            cur.execute(f"ALTER TABLE patients ADD COLUMN {col_name} {col_def}")
            added.append(col_name)
            print(f"  ✅ Added column: patients.{col_name}")
        else:
            print(f"  ⏭️  Column already exists: patients.{col_name}")

    conn.commit()
    conn.close()

    if added:
        print(f"\nMigration complete. Added {len(added)} column(s).")
    else:
        print("\nNo changes needed — database is already up to date.")

if __name__ == "__main__":
    run()
