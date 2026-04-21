from dotenv import load_dotenv; load_dotenv('.env')
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    print("=== FUNCTIONS ===")
    rows = conn.execute(text(
        "SELECT routine_name FROM information_schema.routines "
        "WHERE routine_schema = 'public' AND routine_type = 'FUNCTION' "
        "AND (routine_name LIKE 'fn_%' OR routine_name LIKE 'refresh_%') "
        "ORDER BY routine_name"
    )).fetchall()
    for r in rows: print(f"  {r[0]}")

    print("\n=== TRIGGERS ===")
    rows = conn.execute(text(
        "SELECT trigger_name, event_object_table, action_timing, event_manipulation "
        "FROM information_schema.triggers WHERE trigger_schema = 'public' "
        "ORDER BY event_object_table, trigger_name"
    )).fetchall()
    for r in rows: print(f"  [{r[1]}] {r[0]} ({r[2]} {r[3]})")

    print("\n=== VIEWS ===")
    rows = conn.execute(text(
        "SELECT table_name FROM information_schema.views WHERE table_schema = 'public' ORDER BY table_name"
    )).fetchall()
    for r in rows: print(f"  {r[0]}")

    print("\n=== MATVIEWS ===")
    rows = conn.execute(text(
        "SELECT matviewname FROM pg_matviews WHERE schemaname = 'public' ORDER BY matviewname"
    )).fetchall()
    for r in rows: print(f"  {r[0]}")

    print("\n=== INDEXES ===")
    rows = conn.execute(text(
        "SELECT indexname, tablename FROM pg_indexes "
        "WHERE schemaname = 'public' AND indexname LIKE 'idx_%' ORDER BY tablename, indexname"
    )).fetchall()
    for r in rows: print(f"  [{r[1]}] {r[0]}")

    print("\n=== CHECK CONSTRAINTS ===")
    rows = conn.execute(text(
        "SELECT constraint_name, table_name FROM information_schema.table_constraints "
        "WHERE constraint_type = 'CHECK' AND constraint_schema = 'public' "
        "AND constraint_name LIKE 'chk_%' ORDER BY table_name, constraint_name"
    )).fetchall()
    for r in rows: print(f"  [{r[1]}] {r[0]}")
