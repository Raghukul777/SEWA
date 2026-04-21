"""
SEWA Pydantic Schemas (Request / Response models)
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


# ── Auth ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    hospital_name: str = ""
    department: str = ""
    phone: str = ""
    role: str = "Doctor"

class UserOut(BaseModel):
    id: str
    email: str
    name: str
    hospital_name: str
    department: str = ""
    phone: str = ""
    role: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Patients ────────────────────────────────────────────────────────

class AdmitPatientRequest(BaseModel):
    name: str
    age: int
    gender: str
    bed_number: str
    admission_reason: str = ""
    trajectory: str = "stable"
    medical_history: List[str] = []
    treatment_bundle: Dict[str, Any] = {}
    # Extended patient details
    phone: str = ""
    blood_group: str = ""
    emergency_contact_name: str = ""
    emergency_contact_phone: str = ""
    address: str = ""

class PatientOut(BaseModel):
    patient_id: str
    doctor_id: Optional[str] = None
    name: str
    age: int
    gender: str
    blood_group: str = ""
    bed_number: str
    admission_reason: str
    admission_date: datetime
    trajectory: str
    medical_history: List[Any]
    treatment_bundle: Dict[str, Any]
    status: str
    is_active: bool
    clinical_notes: List[Any] = []
    latest_vitals: Optional[Dict[str, Any]] = None
    # Extended contact details
    phone: str = ""
    emergency_contact_name: str = ""
    emergency_contact_phone: str = ""
    address: str = ""
    # Metadata
    updated_at: Optional[datetime] = None
    active_alert_count: int = 0
    note_count: int = 0

class UpdateTreatmentRequest(BaseModel):
    key: str
    value: Any

class AddNoteRequest(BaseModel):
    text: str
    author: str = "Unknown"


# ── Vital Readings ───────────────────────────────────────────────────

class VitalReadingRequest(BaseModel):
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    temperature: Optional[float] = None
    sbp: Optional[float] = None
    map: Optional[float] = None
    dbp: Optional[float] = None
    respiratory_rate: Optional[float] = None
    lactate: Optional[float] = None
    wbc: Optional[float] = None
    creatinine: Optional[float] = None
    on_vasopressors: bool = False
    infection_suspected: bool = False
    timestamp: Optional[str] = None   # ISO string from simulated frontend

class VitalReadingOut(BaseModel):
    id: int
    patient_id: str
    timestamp: datetime
    heart_rate: Optional[float]
    spo2: Optional[float]
    temperature: Optional[float]
    sbp: Optional[float]
    map: Optional[float]
    dbp: Optional[float]
    respiratory_rate: Optional[float]
    lactate: Optional[float]
    wbc: Optional[float]
    creatinine: Optional[float]

class RiskAssessmentOut(BaseModel):
    riskLevel: str        # LOW | MODERATE | HIGH  (frontend naming)
    criteria: List[str]
    actions: List[str]
    summary: str
    riskScore: float = 0
    ml_risk_level: str = ""
    final_risk_level: str = ""
    clinical_narrative: str = ""
    rules_triggered: List[str] = []

class VitalResponseOut(BaseModel):
    reading: VitalReadingOut
    risk_assessment: RiskAssessmentOut
    alert: Optional[Dict[str, Any]] = None


# ── Alerts ───────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: str
    patient_id: str
    timestamp: datetime
    risk_level: str
    clinical_summary: str
    param_values: Dict[str, Any]
    triggered_criteria: List[str]
    recommended_actions: List[str]
    feedback: str
    is_active: bool

class FeedbackRequest(BaseModel):
    feedback: str    # pending | approved | false_positive


# ── Audit Logs ───────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    severity: str
    patient_id: Optional[str]
    patient_name: Optional[str]
    user_email: str
    event_description: str

class VitalSigns(BaseModel):
    """Real-time patient vitals and labs for core ML inference."""
    heart_rate:        Optional[float] = Field(None, ge=20,  le=300)
    respiratory_rate:  Optional[float] = Field(None, ge=4,   le=60)
    temperature_c:     Optional[float] = Field(None, ge=20,  le=45)
    systolic_bp:       Optional[float] = Field(None, ge=40,  le=250)
    diastolic_bp:      Optional[float] = Field(None, ge=20,  le=180)
    spo2_percent:      Optional[float] = Field(None, ge=50,  le=100)
    wbc_count:         Optional[float] = Field(None, ge=0,   le=200)
    lactate:           Optional[float] = Field(None, ge=0,   le=30)
    creatinine:        Optional[float] = Field(None, ge=0,   le=20)
    bilirubin_total:   Optional[float] = Field(None, ge=0,   le=50)
    bun:               Optional[float] = Field(None, ge=0,   le=300)
    glucose:           Optional[float] = Field(None, ge=20,  le=2000)
    hemoglobin:        Optional[float] = Field(None, ge=2,   le=25)
    platelets:         Optional[float] = Field(None, ge=1,   le=2000)
    hours_since_admission: Optional[float] = Field(0.0, ge=0)
    age:                   Optional[float] = Field(60.0, ge=0, le=120)
    gender:                Optional[int]   = Field(1, ge=0, le=1) # 0:F, 1:M
    patient_id:            Optional[str]   = Field(None)

class RiskExplanation(BaseModel):
    top_features:     List[dict] = Field(default_factory=list)
    clinical_factors: List[str]  = Field(default_factory=list)
    shap_values:      dict       = Field(default_factory=list)

class SepsisAlert(BaseModel):
    """Production-grade sepsis early warning response."""
    patient_id:         Optional[str]
    risk_score:         float = Field(..., description="Unified risk index [0-1]")
    risk_level:         str   = Field(..., description="LOW | MODERATE | HIGH | CRITICAL")
    ml_probability:     float = Field(..., description="Calibrated LightGBM output")
    sirs_score:         int
    qsofa_score:        int
    rule_overrides:     List[str] = Field(default_factory=list)
    explanations:       RiskExplanation
    confidence:         float = Field(..., description="Model confidence score [0-1]")
    model_version:      str
    timestamp:          str
    system_health:      str   = Field("OK", description="OK | DEGRADED | FAILSAFE")

class ModelInfo(BaseModel):
    model_version:   str
    model_type:      str
    n_features:      int
    auroc:           Optional[float]
    calibrated:      bool
    system_status:   str
