"""
SEWA FastAPI Application — Main Entry Point

Run from sewa_final/ directory:
    uvicorn api.main:app --reload --port 8000

Swagger UI available at: http://localhost:8000/docs
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Load .env file before anything else touches os.getenv
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add sewa_final/ parent to path so `sewa` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .database import create_tables, apply_pg_setup, engine
from .auth import router as auth_router
from .patients import router as patients_router
from .vitals import router as vitals_router
from .alerts import router as alerts_router
from .audit import router as audit_router
from .admin import router as admin_router
from .data_admin import router as data_admin_router
from .ws import router as ws_router


# ── Lifespan ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup tasks: create DB tables, apply PG setup, load ML model."""

    # 1. Create all tables (idempotent — uses CREATE IF NOT EXISTS)
    create_tables()
    print("✅  Database tables ready")

    # 2. Apply PostgreSQL triggers, indexes, views, functions
    #    pg_setup.sql is designed to be 100% idempotent — safe to re-run.
    pg_sql_path = Path(__file__).parent / "pg_setup.sql"
    apply_pg_setup(pg_sql_path)

    # 3. Seed demo users if none exist
    _seed_demo_users()
    print("✅  Demo users seeded (if empty)")

    # 3.5. Initialize synthetic data loader (ICU monitoring simulation)
    try:
        from .data_loader import initialize_data_loader
        if initialize_data_loader():
            print("✅  Synthetic patient data loaded and ready")
        else:
            print("⚠️   Synthetic patient data not available — vitals simulation disabled")
    except Exception as e:
        print(f"⚠️   Failed to load synthetic data ({e}) — vitals simulation disabled")

    # 4. Try loading the new CoreMLEngine
    app.state.ml_engine = None
    try:
        from api.ml.inference.risk_engine import CoreMLEngine
        engine_instance = CoreMLEngine()
        if engine_instance.ready:
            app.state.ml_engine = engine_instance
            print(f"✅  New ML Engine loaded successfully")
        else:
            print("⚠️   ML Engine initialization degraded or failed")
            app.state.ml_engine = engine_instance  # Still attach it for failsafe run
    except Exception as e:
        print(f"⚠️   ML model load failed ({e}) — using rule-based fallback only")

    yield  # API is running

    print("🛑  SEWA API shutting down")


def _seed_demo_users():
    """Insert demo users into the DB if none exist yet."""
    from .database import SessionLocal, User
    from .auth import hash_password

    # demo_users = [
    #     {
    #         "id": "D-1002",
    #         "email": "admin@sewa.com",
    #         "password": "Password123",
    #         "name": "Dr. donglee",
    #         "hospital_name": "Central Medical Center",
    #         "department": "Administration",
    #         "role": "Administrator",
    #     },
    # ]

    # db = SessionLocal()
    # try:
    #     for u in demo_users:
    #         existing = db.query(User).filter(User.email == u["email"]).first()
    #         if not existing:
    #             user = User(
    #                 id=u["id"],
    #                 email=u["email"],
    #                 hashed_password=hash_password(u["password"]),
    #                 name=u["name"],
    #                 hospital_name=u["hospital_name"],
    #                 department=u.get("department", ""),
    #                 role=u["role"],
    #             )
    #             db.add(user)
    #     db.commit()
    # finally:
    #     db.close()


# ── App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="SEWA – Sepsis Early Warning Agent API",
    description=(
        "REST API for the SEWA clinical decision-support system. "
        "Provides patient management, real-time vital sign processing with ML risk scoring, "
        "sepsis alerts, and audit logging. "
        "PostgreSQL backend with triggers, materialized views, and JSONB indexing."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────

_origins_raw = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://localhost:3000"
)
ALLOWED_ORIGINS = [o.strip() for o in _origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(vitals_router)
app.include_router(alerts_router)
app.include_router(audit_router)
app.include_router(admin_router)
app.include_router(data_admin_router)  # Data source management endpoints
app.include_router(ws_router)  # Real-time WebSocket vitals stream


# ── Health + system endpoints ─────────────────────────────────────────

@app.get("/health", tags=["system"])
def health():
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    return {"status": "ok", "service": "SEWA API", "version": "2.0.0", "database": db_status}


@app.get("/", tags=["system"])
def root():
    return {
        "message": "SEWA – Sepsis Early Warning Agent API",
        "docs": "/docs",
        "version": "2.0.0",
    }


@app.post("/admin/refresh-stats", tags=["system"])
def refresh_materialized_view(
    # Only admins should call this endpoint
):
    """
    Refresh the mv_patient_stats materialized view.
    Call periodically (e.g. every 5 min via cron) for fast analytics queries.
    """
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("SELECT refresh_patient_stats()"))
        conn.commit()
    return {"message": "mv_patient_stats refreshed successfully"}
