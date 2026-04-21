# SEWA Synthetic Data Integration - Architecture & Data Flow

## System Architecture

### High-Level Overview
```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                            │
│                     Patient Dashboard & Charts                      │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          │ WebSocket: /ws/vitals
                          │ (receives vital updates every 3 seconds)
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│                      FASTAPI BACKEND                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  WebSocket Handler (ws.py)                                 │  │
│  │  - Manage client subscriptions                             │  │
│  │  - Loop every 3s: call simulator.get_next_reading()       │  │
│  │  - Persist vitals to DB                                   │  │
│  │  - Run risk assessment                                    │  │
│  │  - Send to subscribed clients                             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                          │                                           │
│                          ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  simulator.py (MODIFIED)                                   │  │
│  │  - get_next_reading(patient_id)                            │  │
│  │  - Looks up synthetic_data_id from patients table         │  │
│  │  - Calls data_loader.get_next_vitals_from_data()          │  │
│  │  - Returns: {HR, RR, MAP, Temp, SpO2, Lactate, ...}      │  │
│  │  - reset_patient(patient_id)                              │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                          │                                           │
│                          ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  data_loader.py (NEW)                                       │  │
│  │  - initialize_data_loader()         [startup]              │  │
│  │  - get_next_vitals_from_data(id)    [per vital request]   │  │
│  │  - get_patient_data_range(id)       [metadata queries]    │  │
│  │  - get_data_statistics()            [admin queries]       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                          │                                           │
│                          ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  In-Memory CSV Data (pandas DataFrame)                      │  │
│  │  - 48,000 vital readings                                   │  │
│  │  - 1,000 unique synthetic patients                         │  │
│  │  - Columns: patient_id, timestamp, HR, RR, MAP, Temp, ... │  │
│  │  - Tracking: per-patient reading index                     │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  patient_data_sync.py (NEW)                                │  │
│  │  - find_available_synthetic_patient()                      │  │
│  │  - link_patient_to_synthetic_data(db, P-id, S-id)         │  │
│  │  - unlink_patient_from_synthetic_data(db, P-id)           │  │
│  │  - Used by: patients.py (admit), data_admin.py (relink)   │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                          │                                           │
│                          ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  PostgreSQL Database                                        │  │
│  │  - patients table (+ synthetic_data_id, sync timestamps)   │  │
│  │  - vital_readings table                                    │  │
│  │  - alerts table                                            │  │
│  │  - audit_logs table                                        │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Admin Endpoints (data_admin.py) (NEW)                    │  │
│  │  - GET /admin/data/stats                                   │  │
│  │  - GET /admin/data/patient/{id}                            │  │
│  │  - POST /admin/data/patient/{id}/relink                    │  │
│  │  - GET /admin/data/unlinked-patients                       │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          │ /patients, /vitals, /alerts
                          │ (REST endpoints)
                          │
                          ▼
                    (Web UI Forms)
```

---

## Patient Admission Flow (Detailed)

```
STEP 1: Doctor opens Web UI
        │
        ▼
    Form: New Patient
    - Name, Age, Gender, Bed#, Reason, etc.
        │
        ▼
STEP 2: POST /patients
    {
      "name": "John Doe",
      "age": 65,
      "gender": "Male",
      "bed_number": "ICU-101",
      ...
    }
        │
        ▼
STEP 3: API Handler (patients.py → admit_patient)
        │
        ├─► Import functions:
        │   - find_available_synthetic_patient()
        │   - link_patient_to_synthetic_data()
        │
        ├─► Create patient record in memory
        │   patient_id = "P-ABC123"
        │
        ├─► Add to database
        │   db.add(patient)
        │   db.flush()
        │
        ├─► Find available synthetic data
        │   synthetic_id = find_available_synthetic_patient()
        │   → Queries data_loader.get_all_patient_ids()
        │   → Returns: 683 (if available)
        │
        ├─► Link patient to synthetic data
        │   link_patient_to_synthetic_data(db, "P-ABC123", 683)
        │   → UPDATE patients SET synthetic_data_id=683, ...
        │
        ├─► Log admission event
        │   _log_audit(event="patient_admitted", ...)
        │
        └─► Commit to database
            db.commit()
        │
        ▼
STEP 4: Response to Frontend
    {
      "patient_id": "P-ABC123",
      "name": "John Doe",
      "status": "Stable",
      "is_active": true,
      "synthetic_data_id": 683,  ← Returned (for debugging)
      ...
    }
        │
        ▼
STEP 5: Frontend shows success
    "Patient John Doe admitted to ICU-101"
    "Vitals monitoring started"
        │
        ▼
    ✅ Patient Ready for Monitoring
```

---

## Real-Time Vitals Streaming (Detailed)

```
STEP 1: Frontend Opens WebSocket
        │
        websocat ws://localhost:8000/ws/vitals
        │
        ▼
STEP 2: Frontend Subscribes
        {
          "type": "subscribe",
          "patient_ids": ["P-ABC123", "P-XYZ789"]
        }
        │
        ▼
STEP 3: Backend WebSocket Handler (ws.py)
        │
        ├─► Register connection
        │   _connections[websocket] = {"P-ABC123", "P-XYZ789"}
        │
        └─► Start streaming loop (every 3 seconds)
            │
            ▼ (every 3 seconds, per patient)
            for patient_id in subscribed_patients:
                ├─► Call: vitals = simulator.get_next_reading(patient_id)
                │
                ├─► Inside simulator.py:
                │   ├─► db.query("SELECT synthetic_data_id FROM patients WHERE patient_id='P-ABC123'")
                │   │   → Result: synthetic_data_id = 683
                │   │
                │   ├─► Call: data_loader.get_next_vitals_from_data(683)
                │   │
                │   └─► Inside data_loader.py:
                │       ├─► Lookup patient 683 in _synthetic_data DataFrame
                │       │
                │       ├─► Get current reading index (e.g., 42)
                │       │
                │       ├─► Read row 42 from CSV
                │       │   timestamp: "2026-01-01 08:45:05"
                │       │   heart_rate: 82.5
                │       │   map: 75.3
                │       │   lactate: 1.2
                │       │   ... (all vitals)
                │       │
                │       ├─► Increment index to 43
                │       │   _patient_reading_index[683] = 43
                │       │
                │       └─► Return vitals dict
                │
                ├─► Persist to database
                │   reading = VitalReading(
                │       patient_id="P-ABC123",
                │       timestamp=vitals["timestamp"],
                │       heart_rate=vitals["heart_rate"],
                │       ...
                │   )
                │   db.add(reading)
                │
                ├─► Run risk assessment
                │   recent_readings = db.query(VitalReading).filter(...)
                │   risk_level = _run_rule_based_risk(recent_readings)
                │
                ├─► Send to frontend (if subscribed)
                │   {
                │       "type": "vital",
                │       "data": {
                │           "patient_id": "P-ABC123",
                │           "timestamp": "2026-01-01T08:45:05Z",
                │           "heart_rate": 82.5,
                │           "map": 75.3,
                │           "lactate": 1.2,
                │           "spo2": 97.5,
                │           "temperature": 36.8,
                │           "respiratory_rate": 18.2,
                │           "wbc": null,
                │           "creatinine": null,
                │       }
                │   }
                │
                └─► (repeat every 3 seconds)
        │
        ▼
STEP 4: Frontend Receives Updates
        │
        ├─► Update React state
        │   setVitals({...})
        │
        ├─► Re-render charts
        │   VitalsChart.update(newData)
        │
        ├─► Display latest values
        │   HR: 82.5 bpm
        │   MAP: 75.3 mmHg
        │   Lactate: 1.2 mmol/L
        │
        └─► Show trend indicators
            ↑ (increasing) / ↓ (decreasing) / → (stable)
```

---

## Data Source Lookup (Detailed)

```
When vital is requested for patient "P-ABC123":

┌──────────────────────────────────────────────────────┐
│  simulator.get_next_reading("P-ABC123")              │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │  Open DB session             │
        │  db = SessionLocal()          │
        └──────────────┬────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  Query: SELECT synthetic_id  │
        │  FROM patients               │
        │  WHERE patient_id = ?        │
        │  Params: ["P-ABC123"]        │
        └──────────────┬────────────────┘
                       │
            ┌──────────┴──────────┐
            │                     │
            ▼                     ▼
    Found: 683             Not Found: None
    (synthetic_id)         (Patient not in DB
                            or not linked)
    │                      │
    │                      ▼
    │              Return empty vitals
    │              {
    │                "patient_id": "P-ABC123",
    │                "heart_rate": null,
    │                "map": null,
    │                "lactate": null,
    │                ...
    │              }
    │              & Log warning
    │
    ▼
    Call: data_loader.get_next_vitals_from_data(683)
    │
    ├─► Lookup patient 683 in _synthetic_data DataFrame
    │   _synthetic_data[_synthetic_data['patient_id']==683]
    │
    ├─► Check if patient has any data
    │   if empty: return None
    │
    ├─► Get current index for patient 683
    │   current_idx = _patient_reading_index.get(683, 0)
    │   (e.g., 42 - next unread row)
    │
    ├─► Check if index exceeds data length
    │   if current_idx >= len(patient_data):
    │       Reset to 0 (loop back)
    │
    ├─► Get row at current_idx
    │   row = patient_data.iloc[42]
    │   timestamp: "2026-01-01 08:45:05"
    │   heart_rate: 82.5
    │   map: 75.3
    │   temperature: 36.8
    │   lactate: 1.2
    │   spo2: 97.5
    │   respiratory_rate: 18.2
    │   risk_category: 2
    │
    ├─► Increment index for next call
    │   _patient_reading_index[683] = 43
    │
    └─► Build vitals dict and return
        {
          'patient_id': 683,
          'timestamp': '2026-01-01T08:45:05',
          'heart_rate': 82.5,
          'map': 75.3,
          'temperature': 36.8,
          'lactate': 1.2,
          'spo2': 97.5,
          'respiratory_rate': 18.2,
          'wbc': None,
          'creatinine': None,
          'risk_category': 2
        }
    │
    ▼
Back in simulator.get_next_reading():
    │
    ├─► Ensure patient_id is registered ID (not synthetic)
    │   vitals['patient_id'] = 'P-ABC123'
    │
    └─► Return to WebSocket handler
        {
          'patient_id': 'P-ABC123',
          'timestamp': '2026-01-01T08:45:05',
          'heart_rate': 82.5,
          ...
        }
```

---

## Admin Data Management

```
Admin Dashboard Use Cases:

┌─────────────────────────────────────────────────────────────┐
│ GET /admin/data/stats                                       │
│ View overall system health                                  │
│                                                             │
│ Response:                                                   │
│ {                                                           │
│   "synthetic_data": {                                       │
│     "total_readings": 48000,                                │
│     "unique_patients": 1000,                                │
│     "date_range_start": "2026-01-01T00:00:00",              │
│     "date_range_end": "2026-01-01T11:45:00"                 │
│   },                                                        │
│   "database": {                                             │
│     "total_patients": 5,           ← 5 real patients        │
│     "patients_linked": 5,          ← all have synthetic data │
│     "active_patients": 5,          ← all are monitored      │
│     "active_with_data": 5          ← all can receive data   │
│   },                                                        │
│   "integration_status": "healthy"                           │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ GET /admin/data/patient/P-ABC123                            │
│ Check specific patient's data source                        │
│                                                             │
│ Response:                                                   │
│ {                                                           │
│   "patient_id": "P-ABC123",                                 │
│   "name": "John Doe",                                       │
│   "synthetic_data_id": 683,        ← Linked to patient 683  │
│   "data_sync_started_at": "2026-01-15T10:30:00",            │
│   "data_range": {                                           │
│     "patient_id": 683,                                      │
│     "min_time": "2026-01-01T00:00:00",                      │
│     "max_time": "2026-01-01T11:45:00",                      │
│     "reading_count": 48             ← 48 readings available │
│   },                                                        │
│   "status": "Stable",                                       │
│   "is_active": true                                         │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ GET /admin/data/unlinked-patients                           │
│ Find patients that need synthetic data assigned             │
│                                                             │
│ Response:                                                   │
│ {                                                           │
│   "count": 2,                                               │
│   "patients": [                                             │
│     {                                                       │
│       "patient_id": "P-XYZ789",                             │
│       "name": "Jane Smith",                                 │
│       "admission_date": "2026-01-15T14:20:00",              │
│       "bed_number": "ICU-102"                               │
│     },                                                      │
│     ...                                                     │
│   ]                                                         │
│ }                                                           │
│                                                             │
│ Action: Relink these patients                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ POST /admin/data/patient/P-ABC123/relink                    │
│ Reassign synthetic data (e.g., when stream exhausted)      │
│                                                             │
│ Request:                                                    │
│ {                                                           │
│   "synthetic_data_id": 750                                  │
│ }                                                           │
│                                                             │
│ Response:                                                   │
│ {                                                           │
│   "status": "success",                                      │
│   "message": "Patient P-ABC123 relinked to synthetic...",   │
│   "patient_id": "P-ABC123",                                 │
│   "synthetic_data_id": 750,                                 │
│   "data_range": {                                           │
│     "reading_count": 48,                                    │
│     ...                                                     │
│   }                                                         │
│ }                                                           │
│                                                             │
│ Effect:                                                     │
│ - Update DB: synthetic_data_id = 750                        │
│ - Reset stream index for patient 750                        │
│ - Resume vitals streaming with new data source             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Streaming Example Timeline

```
Time    Action                          What's in Memory
─────────────────────────────────────────────────────────────

09:00   API starts
        data_loader.initialize()        CSV loaded into pandas
        _synthetic_data = DataFrame
        _patient_reading_index = {}

09:05   Doctor admits patient P-ABC123
        find_available_synthetic_patient() → 683
        link_patient_to_synthetic_data(..., 683)
        DB: P-ABC123.synthetic_data_id = 683

09:06   Frontend subscribes to P-ABC123 WebSocket

09:07   ws.py loops: simulator.get_next_reading("P-ABC123")
        │
        └─→ DB query: synthetic_id = 683
            data_loader.get_next_vitals_from_data(683)
            │
            ├─ _patient_reading_index[683] = 0 (first call)
            ├─ Read row 0 from CSV for patient 683
            ├─ Increment index: _patient_reading_index[683] = 1
            └─ Return: {HR: 82.5, MAP: 75.3, ...}
        
        Message sent to frontend

09:10   ws.py loops again (3 seconds later)
        simulator.get_next_reading("P-ABC123")
        │
        └─→ DB query: synthetic_id = 683
            data_loader.get_next_vitals_from_data(683)
            │
            ├─ _patient_reading_index[683] = 1 (from last call)
            ├─ Read row 1 from CSV for patient 683
            ├─ Increment index: _patient_reading_index[683] = 2
            └─ Return: {HR: 81.2, MAP: 76.1, ...}  ← DIFFERENT VALUES!
        
        Message sent to frontend

09:13   ws.py loops again
        simulator.get_next_reading("P-ABC123")
        │
        └─→ DB query: synthetic_id = 683
            data_loader.get_next_vitals_from_data(683)
            │
            ├─ _patient_reading_index[683] = 2
            ├─ Read row 2 from CSV for patient 683
            ├─ Increment index: _patient_reading_index[683] = 3
            └─ Return: {HR: 80.5, MAP: 75.8, ...}  ← NEXT in sequence
        
        Message sent to frontend

... (continues every 3 seconds)

14:00   Patient data reaches end (e.g., row 47 out of 48)
        _patient_reading_index[683] = 48 (out of bounds)
        │
        └─→ get_next_vitals_from_data(683)
            ├─ Check: 48 >= len(patient_data) = 48? YES
            ├─ Reset index: _patient_reading_index[683] = 0
            └─ Return: {HR: 82.5, MAP: 75.3, ...}  ← LOOPS BACK
        
        Streaming continues from start

14:30   Admin decides to relink (wants different data pattern)
        POST /admin/data/patient/P-ABC123/relink
        ├─ Update DB: synthetic_data_id = 750
        ├─ Reset index: _patient_reading_index[750] = 0
        └─ Streaming resumes with patient 750's data
        
        Next vital request uses synthetic_data_id = 750
```

---

## Edge Cases & Handling

```
CASE 1: Patient Not Linked to Synthetic Data
  └─ Cause: New patient, no synthetic data available, or DB error
  └─ Behavior: get_next_reading() returns {patient_id, timestamp, all nulls}
  └─ Frontend: Shows "No vitals available" message
  └─ Fix: Admin uses /admin/data/patient/P-ID/relink to assign data

CASE 2: No More Synthetic Data for Patient
  └─ Cause: Reached end of CSV rows for that synthetic patient
  └─ Behavior: data_loader loops back to row 0
  └─ Frontend: Vitals continue but pattern repeats
  └─ Fix: Admin relinks to different synthetic patient if needed

CASE 3: Multiple Patients Same Synthetic Data
  └─ Cause: Manual error or more real patients than synthetic patients
  └─ Behavior: Both patients stream from same CSV (independent indices)
  └─ Frontend: Both show vitals but different timestamps
  └─ Expected: Allowed, but not ideal (same patterns for both)

CASE 4: Patient Discharge
  └─ Cause: Doctor discharges patient
  └─ Behavior: data_sync_ended_at timestamp set, synthetic_data_id stays
  └─ Effect: Patient can be re-admitted and linked again
  └─ Admin: Synthetic data becomes available for reassignment

CASE 5: CSV File Changes
  └─ Cause: Replace CSV with new data
  └─ Behavior: Requires API restart to reload
  └─ Fix: Initialize data_loader is idempotent, safe to restart
  └─ Note: Current reading indices reset on restart
```

---

## Comparison: Before vs After

```
┌──────────────────────────┬──────────────────┬───────────────────────┐
│ Aspect                   │ BEFORE           │ AFTER                 │
├──────────────────────────┼──────────────────┼───────────────────────┤
│ Data Source              │ Generated (math) │ CSV file (real-like)   │
│ Realism                  │ Generic patterns │ Realistic time series  │
│ Consistency              │ Random each time │ Sequential from data   │
│ Patient Patterns         │ Same for all     │ Unique per patient     │
│ Reproducibility          │ Non-reproducible │ Deterministic          │
│ Memory Usage             │ None             │ CSV in RAM (~50MB)     │
│ Computation              │ Math + RNG       │ Lookups only (O(1))    │
│ DB Columns               │ None             │ synthetic_data_id (+2) │
│ Admin Control            │ None             │ Full management UI     │
│ Transition to Real Data  │ Hard             │ 1 file change (easy)   │
│ Patient-Data Link        │ None             │ Persistent (DB)        │
│ Troubleshooting          │ Difficult        │ Clear audit trail      │
└──────────────────────────┴──────────────────┴───────────────────────┘
```

---

## Summary Diagram

```
                    ┌─────────────────────────┐
                    │   Synthetic Data CSV    │
                    │  (48,000 readings)      │
                    │  (1,000 patients)       │
                    └────────────┬────────────┘
                                 │
                                 │ Load on startup
                                 │
                    ┌────────────▼────────────┐
                    │   data_loader.py        │
                    │  In-memory DataFrame    │
                    │  Streaming indices      │
                    └────────────┬────────────┘
                                 │
                    Per-patient: │
                    ├─► 1: Read row N
                    ├─► 2: Increment index
                    └─► 3: Return vitals
                                 │
                    ┌────────────▼────────────┐
                    │   simulator.py          │
                    │  get_next_reading()     │
                    │  - Lookup synthetic_id  │
                    │  - Call data_loader     │
                    │  - Return vitals        │
                    └────────────┬────────────┘
                                 │
                    Every 3 seconds:
                    ├─► Persist to DB
                    ├─► Assess risk
                    └─► Push to frontend
                                 │
                    ┌────────────▼────────────┐
                    │   Frontend (React)      │
                    │  Charts + Monitoring    │
                    │  Updated in real-time   │
                    └─────────────────────────┘
```

---

This architecture ensures:
✅ Realistic ICU monitoring simulation
✅ Deterministic, reproducible behavior
✅ Easy transition to real devices
✅ Full admin control over data allocation
✅ No frontend changes needed
✅ Scalable to hundreds of concurrent patients

