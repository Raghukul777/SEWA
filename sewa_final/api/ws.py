"""
SEWA — WebSocket Real-Time Vitals Stream
==========================================
Endpoint: ws://localhost:8000/ws/vitals

Protocol:
  Client → Server:  { "type": "subscribe", "patient_ids": ["P-001", "P-002", ...] }
                    { "type": "unsubscribe", "patient_ids": ["P-001"] }

  Server → Client:  { "type": "vital", "data": { patient_id, timestamp, heart_rate, ... } }
                    { "type": "alert", "data": { id, patient_id, risk_level, clinical_summary, ... } }
                    { "type": "status", "data": { patient_id, connected: true } }
                    { "type": "ping" }

Device Integration:
  When real ICU device is connected, only simulator.py changes.
  This file, the DB schema, and the frontend hook all stay identical.
"""

import asyncio
import json
import uuid
import traceback
from datetime import datetime
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import SessionLocal, Patient, VitalReading, Alert
from .simulator import get_next_reading
from .vitals import _run_rule_based_risk

router = APIRouter(tags=["websocket"])

# ── Connection Registry ────────────────────────────────────────────────────────
_connections: Dict[WebSocket, Set[str]] = {}


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _safe_send(ws: WebSocket, payload: dict) -> bool:
    """Send JSON to client; return False if connection is dead."""
    try:
        await ws.send_json(payload)
        return True
    except Exception:
        return False


def _persist_and_assess(patient_id: str, vitals: dict) -> tuple[dict, dict | None]:
    """
    Write vital to DB, run risk assessment, conditionally create alert.
    Returns (reading_dict, alert_dict | None).
    """
    db: Session = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            return vitals, None

        ts_str = vitals.get("timestamp", datetime.utcnow().isoformat())
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            ts = datetime.utcnow()

        # Skip if all vital values are None (no data available)
        vital_keys = ["heart_rate", "spo2", "temperature", "map",
                       "respiratory_rate", "lactate", "wbc", "creatinine"]
        if all(vitals.get(k) is None for k in vital_keys):
            return vitals, None

        reading = VitalReading(
            patient_id=patient_id,
            timestamp=ts,
            heart_rate=vitals.get("heart_rate"),
            spo2=vitals.get("spo2"),
            temperature=vitals.get("temperature"),
            map=vitals.get("map"),
            respiratory_rate=vitals.get("respiratory_rate"),
            lactate=vitals.get("lactate"),
            wbc=vitals.get("wbc"),
            creatinine=vitals.get("creatinine"),
        )
        db.add(reading)
        db.flush()

        recent = (
            db.query(VitalReading)
            .filter(VitalReading.patient_id == patient_id)
            .order_by(VitalReading.timestamp.desc())
            .limit(20)
            .all()
        )
        recent = list(reversed(recent))
        
        # Evaluate ML Risk
        try:
            from .main import app
            engine = app.state.ml_engine
        except Exception:
            engine = None
            
        if engine and hasattr(engine, "predict"):
            from .schemas import VitalSigns
            vs = VitalSigns(
                patient_id=patient_id,
                heart_rate=vitals.get("heart_rate"),
                spo2_percent=vitals.get("spo2"),
                temperature_c=vitals.get("temperature"),
                systolic_bp=vitals.get("sbp"),
                diastolic_bp=vitals.get("dbp"),
                map=vitals.get("map"),
                respiratory_rate=vitals.get("respiratory_rate"),
                lactate=vitals.get("lactate"),
                wbc_count=vitals.get("wbc"),
                creatinine=vitals.get("creatinine"),
                age=patient.age,
                gender=1 if patient.gender.lower() == 'male' else 0,
                hours_since_admission=(datetime.utcnow() - patient.admission_date.replace(tzinfo=None)).total_seconds() / 3600 if patient.admission_date else 0
            )
            try:
                alert_obj = engine.predict(vs)
                
                clinical_factors = alert_obj.rule_overrides.copy()
                if alert_obj.explanations and alert_obj.explanations.top_features:
                    clinical_factors.extend([f"{f['feature']} (impact: {f['impact']})" for f in alert_obj.explanations.top_features])
                
                risk = {
                    "riskLevel": alert_obj.risk_level,
                    "criteria": clinical_factors,
                    "actions": ["Notify attending physician!"] if alert_obj.risk_level in ("HIGH", "CRITICAL") else ["Monitor vitals closely"],
                    "summary": " | ".join(alert_obj.rule_overrides) if alert_obj.rule_overrides else "ML Risk Assessment completed.",
                    "riskScore": alert_obj.risk_score,
                }
            except Exception as e:
                print(f"[WS ML] Predict failed: {e}")
                risk = _run_rule_based_risk(recent)
        else:
            risk = _run_rule_based_risk(recent)

        status_map = {"LOW": "Stable", "MODERATE": "Warning", "HIGH": "Critical", "CRITICAL": "Critical"}
        new_status = status_map.get(risk["riskLevel"], "Stable")
        if patient.status != new_status:
            patient.status = new_status

        alert_dict = None

        # ── If patient is stable, auto-resolve any open pending alerts ────────
        if risk["riskLevel"] == "LOW":
            db.query(Alert).filter(
                Alert.patient_id == patient_id,
                Alert.feedback == "pending",
                Alert.is_active == True,
            ).update({"is_active": False, "feedback": "auto_resolved"}, synchronize_session=False)

        elif risk["riskLevel"] in ("MODERATE", "HIGH", "CRITICAL"):
            from datetime import timedelta
            now = datetime.utcnow()

            # Rule 1: Block if there is already an ACTIVE unresolved alert for this patient
            # Doctor must review & give feedback before a new one can be raised
            active_pending = db.query(Alert).filter(
                Alert.patient_id == patient_id,
                Alert.feedback == "pending",
                Alert.is_active == True,
            ).first()

            # Rule 2: Global 5-minute cooldown per patient — slows down burst alerts
            five_mins_ago = now - timedelta(minutes=5)
            any_recent = db.query(Alert).filter(
                Alert.patient_id == patient_id,
                Alert.timestamp >= five_mins_ago
            ).first()

            # Rule 3: Same-risk-level block for 30 minutes — no exact duplicates
            thirty_mins_ago = now - timedelta(minutes=30)
            same_level_recent = db.query(Alert).filter(
                Alert.patient_id == patient_id,
                Alert.risk_level == risk["riskLevel"],
                Alert.timestamp >= thirty_mins_ago
            ).first()

            suppressed = bool(active_pending) or bool(any_recent) or bool(same_level_recent)

            if not suppressed:
                # ── Final existence gate: one last check before writing to DB ──
                # Guards against race conditions between concurrent patient streams
                already_in_db = db.query(Alert).filter(
                    Alert.patient_id == patient_id,
                    Alert.risk_level == risk["riskLevel"],
                    Alert.feedback == "pending",
                    Alert.is_active == True,
                ).first()

                if already_in_db:
                    # Alert already exists — return it so frontend stays in sync
                    alert_dict = {
                        "id": already_in_db.id,
                        "patient_id": patient_id,
                        "timestamp": already_in_db.timestamp.isoformat(),
                        "risk_level": already_in_db.risk_level,
                        "clinical_summary": already_in_db.clinical_summary,
                        "param_values": already_in_db.param_values,
                        "triggered_criteria": already_in_db.triggered_criteria,
                        "recommended_actions": already_in_db.recommended_actions,
                        "feedback": already_in_db.feedback,
                        "is_active": already_in_db.is_active,
                    }
                else:
                    alert_id = str(uuid.uuid4())
                    vital_snapshot = {k: vitals.get(k) for k in vital_keys}
                    alert = Alert(
                        id=alert_id,
                        patient_id=patient_id,
                        timestamp=ts,
                        risk_level=risk["riskLevel"],
                        clinical_summary=risk["summary"],
                        param_values=vital_snapshot,
                        triggered_criteria=risk["criteria"],
                        recommended_actions=risk["actions"],
                        feedback="pending",
                        is_active=True,
                    )
                    db.add(alert)
                    alert_dict = {
                        "id": alert_id,
                        "patient_id": patient_id,
                        "timestamp": ts.isoformat(),
                        "risk_level": risk["riskLevel"],
                        "clinical_summary": risk["summary"],
                        "param_values": vital_snapshot,
                        "triggered_criteria": risk["criteria"],
                        "recommended_actions": risk["actions"],
                        "feedback": "pending",
                        "is_active": True,
                    }

        # Attempt commit — the unique partial index on alerts will reject
        # any duplicate active+pending alert even under concurrent stream tasks
        from sqlalchemy.exc import IntegrityError
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # Another concurrent task already inserted an alert for this patient
            # — that's fine, just clear our local alert_dict so we don't re-broadcast
            alert_dict = None
            print(f"[WS] Duplicate alert blocked by DB constraint for {patient_id} (race condition caught)")

        reading_dict = {
            "patient_id": patient_id,
            "timestamp": ts.isoformat(),
            "heart_rate": reading.heart_rate,
            "spo2": reading.spo2,
            "temperature": reading.temperature,
            "map": reading.map,
            "respiratory_rate": reading.respiratory_rate,
            "lactate": reading.lactate,
            "wbc": reading.wbc,
            "creatinine": reading.creatinine,
        }
        return reading_dict, alert_dict

    except Exception as e:
        db.rollback()
        print(f"[WS] DB error for {patient_id}: {e}")
        traceback.print_exc()
        return vitals, None
    finally:
        db.close()


def _get_patient_info(patient_id: str) -> dict | None:
    """Fetch trajectory for a patient from DB."""
    db: Session = SessionLocal()
    try:
        p = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not p:
            return None
        return {
            "trajectory": getattr(p, "trajectory", "stable") or "stable",
            "initial_vitals": None,
        }
    finally:
        db.close()


# ── Per-patient streaming task ─────────────────────────────────────────────────

async def _patient_stream_task(patient_id: str):
    """
    Continuously generates/reads vitals for one patient every 3 seconds,
    then broadcasts to all subscribed WebSocket connections.

    This task keeps running as long as at least one client is subscribed.
    If all clients disconnect, the task waits up to 30s for a reconnection
    (handles React StrictMode re-mount and brief network blips).
    """
    info = await asyncio.to_thread(_get_patient_info, patient_id)
    if not info:
        print(f"[WS] Patient {patient_id} not found — stream aborted")
        return

    trajectory = info["trajectory"]
    initial_vitals = info["initial_vitals"]
    no_subscriber_count = 0
    MAX_IDLE_CYCLES = 10  # 10 × 3s = 30s grace period before stopping

    print(f"[WS] ▶ Stream started: {patient_id} (trajectory: {trajectory})")

    while True:
        subscribers = [ws for ws, ids in _connections.items() if patient_id in ids]

        if not subscribers:
            no_subscriber_count += 1
            if no_subscriber_count >= MAX_IDLE_CYCLES:
                print(f"[WS] ⏹ No subscribers for {patient_id} after {MAX_IDLE_CYCLES * 3}s — stream stopped")
                break
            # Wait and check again (handles React StrictMode unmount → remount)
            await asyncio.sleep(3)
            continue
        else:
            no_subscriber_count = 0  # Reset grace period

        try:
            # ── Get vitals from data source ──────────────────────────────
            vitals = await asyncio.to_thread(
                get_next_reading, patient_id, trajectory, initial_vitals
            )

            # Skip broadcasting if all vitals are None (no data linked)
            vital_keys = ["heart_rate", "spo2", "temperature", "map",
                          "respiratory_rate", "lactate"]
            if all(vitals.get(k) is None for k in vital_keys):
                print(f"[WS] ⚠ {patient_id}: No vitals data (check synthetic_data_id mapping)")
                await asyncio.sleep(5)  # Slower retry when no data
                continue

            # ── Persist + risk assess ─────────────────────────────────────
            reading_dict, alert_dict = await asyncio.to_thread(
                _persist_and_assess, patient_id, vitals
            )

            # ── Broadcast to all subscribed clients ───────────────────────
            dead_connections = []
            for ws in subscribers:
                ok = await _safe_send(ws, {"type": "vital", "data": reading_dict})
                if not ok:
                    dead_connections.append(ws)
                    continue
                if alert_dict:
                    await _safe_send(ws, {"type": "alert", "data": alert_dict})

            for ws in dead_connections:
                _connections.pop(ws, None)

        except Exception as e:
            print(f"[WS] ✗ Error in stream for {patient_id}: {e}")
            traceback.print_exc()

        await asyncio.sleep(3)


# Tracks running tasks per patient
_stream_tasks: Dict[str, asyncio.Task] = {}


def _ensure_stream(patient_id: str):
    """Start a streaming task for patient_id if not already running."""
    task = _stream_tasks.get(patient_id)
    if task is None or task.done():
        t = asyncio.create_task(_patient_stream_task(patient_id))
        _stream_tasks[patient_id] = t


# ── WebSocket Endpoint ─────────────────────────────────────────────────────────

@router.websocket("/ws/vitals")
async def vitals_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time vital streaming.

    Connect: ws://localhost:8000/ws/vitals?token=<JWT>
    
    Send: { "type": "subscribe", "patient_ids": ["P-001"] }
    Recv: { "type": "vital", "data": {...} } | { "type": "alert", "data": {...} }
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    from .auth import decode_token
    try:
        user = decode_token(token)
    except Exception:
        await websocket.close(code=4003, reason="Invalid token")
        return

    await websocket.accept()
    _connections[websocket] = set()
    user_id = user.get('sub', 'unknown')
    print(f"[WS] ✓ Connected: {user_id}")

    # Keepalive ping
    async def _ping_loop():
        try:
            while websocket in _connections:
                await asyncio.sleep(25)
                ok = await _safe_send(websocket, {"type": "ping"})
                if not ok:
                    break
        except Exception:
            pass

    ping_task = asyncio.create_task(_ping_loop())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            patient_ids = msg.get("patient_ids", [])

            if msg_type == "subscribe":
                for pid in patient_ids:
                    _connections[websocket].add(pid)
                    _ensure_stream(pid)
                print(f"[WS] 📡 Subscribed: {patient_ids}")

                # Send immediate acknowledgement (helps frontend know it's connected)
                await _safe_send(websocket, {
                    "type": "status",
                    "data": {"subscribed": patient_ids, "connected": True}
                })

            elif msg_type == "unsubscribe":
                for pid in patient_ids:
                    _connections[websocket].discard(pid)
                print(f"[WS] Unsubscribed: {patient_ids}")

    except WebSocketDisconnect:
        print(f"[WS] ✗ Disconnected: {user_id}")
    except Exception as e:
        print(f"[WS] ✗ Error: {e}")
    finally:
        _connections.pop(websocket, None)
        ping_task.cancel()
