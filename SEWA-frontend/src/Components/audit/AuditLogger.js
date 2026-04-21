import { base44 } from '@/api/base44Client';

/**
 * Comprehensive Audit Logger for SEWA
 * Logs all significant events for compliance and clinical review
 */

class AuditLogger {
  constructor() {
    this.currentUser = null;
    this.initialized = false;
  }

  async initialize() {
    if (this.initialized) return;
    
    try {
      const user = await base44.auth.me();
      this.currentUser = user;
      this.initialized = true;
    } catch (error) {
      // User might not be logged in - continue without user context
      this.currentUser = { email: 'system@sewa.local', full_name: 'System' };
      this.initialized = true;
    }
  }

  async log({
    eventType,
    severity = 'info',
    patientId = null,
    patientName = null,
    description,
    metadata = {},
    previousState = null,
    newState = null,
    alertId = null,
    riskLevel = null
  }) {
    try {
      await this.initialize();

      const logEntry = {
        timestamp: new Date().toISOString(),
        event_type: eventType,
        severity,
        patient_id: patientId,
        patient_name: patientName,
        user_email: this.currentUser?.email || 'system@sewa.local',
        event_description: description,
        event_metadata: metadata,
        previous_state: previousState,
        new_state: newState,
        alert_id: alertId,
        risk_level: riskLevel
      };

      await base44.entities.AuditLog.create(logEntry);
      
      // Also log to console in development
      if (process.env.NODE_ENV === 'development') {
        console.log('[AUDIT]', eventType, description);
      }
    } catch (error) {
      console.error('Failed to write audit log:', error);
      // Don't throw - audit logging failure shouldn't break the app
    }
  }

  // Specific logging methods for common events
  
  async logVitalReading(patient, vitals) {
    await this.log({
      eventType: 'vital_reading_generated',
      severity: 'info',
      patientId: patient.patient_id,
      patientName: patient.name,
      description: `New vital signs recorded for ${patient.name}`,
      metadata: {
        heart_rate: vitals.heart_rate,
        respiratory_rate: vitals.respiratory_rate,
        map: vitals.map,
        spo2: vitals.spo2,
        temperature: vitals.temperature,
        lactate: vitals.lactate,
        timestamp: vitals.timestamp
      }
    });
  }

  async logAlertGenerated(patient, alert, riskAssessment) {
    await this.log({
      eventType: 'alert_generated',
      severity: alert.risk_level === 'HIGH' ? 'critical' : 'warning',
      patientId: patient.patient_id,
      patientName: patient.name,
      description: `${alert.risk_level} risk alert generated for ${patient.name}`,
      alertId: alert.id,
      riskLevel: alert.risk_level,
      metadata: {
        clinical_summary: alert.clinical_summary,
        triggered_criteria: alert.triggered_criteria,
        recommended_actions: alert.recommended_actions,
        risk_score: riskAssessment.riskScore
      }
    });
  }

  async logAlertFeedback(patient, alert, feedback, notes = null) {
    await this.log({
      eventType: 'alert_feedback_submitted',
      severity: 'info',
      patientId: patient.patient_id,
      patientName: patient.name,
      description: `Clinician marked alert as ${feedback} for ${patient.name}`,
      alertId: alert.id,
      riskLevel: alert.risk_level,
      previousState: { feedback: alert.feedback },
      newState: { feedback, notes },
      metadata: {
        alert_risk_level: alert.risk_level,
        alert_timestamp: alert.timestamp,
        feedback_value: feedback,
        notes: notes
      }
    });
  }

  async logRiskLevelChange(patient, previousRisk, newRisk, criteria) {
    await this.log({
      eventType: 'risk_level_changed',
      severity: newRisk === 'HIGH' ? 'critical' : newRisk === 'MODERATE' ? 'warning' : 'info',
      patientId: patient.patient_id,
      patientName: patient.name,
      description: `Risk level changed from ${previousRisk} to ${newRisk} for ${patient.name}`,
      riskLevel: newRisk,
      previousState: { risk_level: previousRisk },
      newState: { risk_level: newRisk },
      metadata: {
        triggered_criteria: criteria
      }
    });
  }

  async logPatientStatusChange(patient, previousStatus, newStatus) {
    await this.log({
      eventType: 'patient_status_changed',
      severity: newStatus === 'Critical' ? 'critical' : 'info',
      patientId: patient.patient_id,
      patientName: patient.name,
      description: `Patient status changed from ${previousStatus} to ${newStatus} for ${patient.name}`,
      previousState: { status: previousStatus },
      newState: { status: newStatus }
    });
  }

  async logSimulationPaused() {
    await this.log({
      eventType: 'simulation_paused',
      severity: 'info',
      description: 'Real-time simulation paused by user',
      metadata: {
        timestamp: new Date().toISOString()
      }
    });
  }

  async logSimulationResumed() {
    await this.log({
      eventType: 'simulation_resumed',
      severity: 'info',
      description: 'Real-time simulation resumed by user',
      metadata: {
        timestamp: new Date().toISOString()
      }
    });
  }

  async logSystemInitialized(patientCount) {
    await this.log({
      eventType: 'system_initialized',
      severity: 'info',
      description: `SEWA system initialized with ${patientCount} patients`,
      metadata: {
        patient_count: patientCount,
        timestamp: new Date().toISOString()
      }
    });
  }

  async logPatientSelected(patient) {
    await this.log({
      eventType: 'patient_selected',
      severity: 'info',
      patientId: patient.patient_id,
      patientName: patient.name,
      description: `Clinician viewed details for ${patient.name}`,
      metadata: {
        patient_status: patient.status,
        bed_number: patient.bed_number
      }
    });
  }
}

// Export singleton instance
export const auditLogger = new AuditLogger();