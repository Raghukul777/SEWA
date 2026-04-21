export const MOCK_AUDIT_LOGS = [
    {
        id: '1',
        timestamp: new Date().toISOString(),
        event_type: 'vital_reading_generated',
        severity: 'info',
        patient_id: 'P-1001',
        patient_name: 'Robert Chen',
        user_email: 'system',
        event_description: 'Vital signs logged: Stable parameters'
    },
    {
        id: '2',
        timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
        event_type: 'vital_reading_generated',
        severity: 'warning',
        patient_id: 'P-1002',
        patient_name: 'Maria Garcia',
        user_email: 'system',
        event_description: 'Vital signs logged: Concerning trends detected'
    },
    {
        id: '3',
        timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
        event_type: 'alert_generated',
        severity: 'critical',
        patient_id: 'P-1003',
        patient_name: 'James Wilson',
        user_email: 'system',
        event_description: 'Sepsis alert triggered: Sustained hypotension'
    },
    {
        id: '4',
        timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
        event_type: 'alert_feedback_submitted',
        severity: 'info',
        patient_id: 'P-1003',
        patient_name: 'James Wilson',
        user_email: 'dr.smith@hospital.com',
        event_description: 'Alert validated by clinician'
    },
    {
        id: '5',
        timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
        event_type: 'risk_level_changed',
        severity: 'warning',
        patient_id: 'P-1002',
        patient_name: 'Maria Garcia',
        user_email: 'system',
        event_description: 'Risk level elevated to MODERATE'
    }
];
