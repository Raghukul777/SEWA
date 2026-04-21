"""
SEWA Audit Log Routes
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .database import get_db, AuditLog
from .auth import get_current_user, User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=List[dict])
def get_audit_logs(
    event_type:  Optional[str] = Query(None),
    severity:    Optional[str] = Query(None),
    since_days:  Optional[int] = Query(None),
    patient_id:  Optional[str] = Query(None),
    limit:       int = Query(500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(AuditLog)

    if event_type and event_type != "all":
        query = query.filter(AuditLog.event_type == event_type)
    if severity and severity != "all":
        query = query.filter(AuditLog.severity == severity)
    if patient_id:
        query = query.filter(AuditLog.patient_id == patient_id)
    if since_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=since_days)
        query = query.filter(AuditLog.timestamp >= cutoff)

    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "event_type": log.event_type,
            "severity": log.severity,
            "patient_id": log.patient_id,
            "patient_name": log.patient_name,
            "user_email": log.user_email,
            "event_description": log.event_description,
        }
        for log in logs
    ]
