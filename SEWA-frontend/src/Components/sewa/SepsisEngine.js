// SEWA Sepsis Early Warning Engine
// Rule-based, transparent, explainable clinical decision support

/**
 * Analyzes vital readings history and returns risk assessment
 * Uses trend-based reasoning, not single thresholds
 */
export function analyzePatientRisk(readings, patient) {
  if (!readings || readings.length === 0) {
    return { riskLevel: 'LOW', criteria: [], actions: [], summary: 'No data available' };
  }

  const criteria = [];
  const actions = [];
  let riskScore = 0;

  // Get recent readings (last 5 for trend analysis)
  const recentReadings = readings.slice(-5);
  const latestReading = readings[readings.length - 1];

  // === RULE 1: Sustained Hypotension ===
  // MAP < 65 mmHg for 2+ consecutive readings
  const lowMAPCount = recentReadings.filter(r => r.map && r.map < 65).length;
  if (lowMAPCount >= 2) {
    criteria.push(`Sustained hypotension: MAP < 65 mmHg in ${lowMAPCount} of last ${recentReadings.length} readings`);
    actions.push('Consider fluid resuscitation (30 mL/kg crystalloid)');
    actions.push('Assess for vasopressor requirement');
    riskScore += lowMAPCount >= 3 ? 3 : 2;
  }

  // === RULE 2: Rising Lactate Trend ===
  // Lactate increasing over 3+ readings
  const lactateReadings = recentReadings.filter(r => r.lactate != null).map(r => r.lactate);
  if (lactateReadings.length >= 3) {
    let risingCount = 0;
    for (let i = 1; i < lactateReadings.length; i++) {
      if (lactateReadings[i] > lactateReadings[i - 1]) risingCount++;
    }
    if (risingCount >= 2) {
      const latestLactate = lactateReadings[lactateReadings.length - 1];
      criteria.push(`Rising lactate trend: ${lactateReadings[0].toFixed(1)} → ${latestLactate.toFixed(1)} mmol/L`);
      actions.push('Repeat lactate measurement in 2-4 hours');
      if (latestLactate > 2) {
        actions.push('Initiate sepsis workup if not already done');
        riskScore += 2;
      }
      riskScore += latestLactate > 4 ? 3 : 1;
    }
  }

  // === RULE 3: Sustained Tachypnea ===
  // RR > 22 for 2+ consecutive readings
  const highRRCount = recentReadings.filter(r => r.respiratory_rate && r.respiratory_rate > 22).length;
  if (highRRCount >= 2) {
    criteria.push(`Sustained tachypnea: RR > 22/min in ${highRRCount} of last ${recentReadings.length} readings`);
    actions.push('Monitor for respiratory distress');
    actions.push('Consider arterial blood gas analysis');
    riskScore += highRRCount >= 3 ? 2 : 1;
  }

  // === RULE 4: Fever or Hypothermia ===
  const tempReadings = recentReadings.filter(r => r.temperature != null);
  const feverCount = tempReadings.filter(r => r.temperature > 38.3).length;
  const hypothermiaCount = tempReadings.filter(r => r.temperature < 36).length;
  if (feverCount >= 2) {
    criteria.push(`Persistent fever: Temperature > 38.3°C in ${feverCount} readings`);
    actions.push('Obtain blood cultures if not done');
    riskScore += 1;
  }
  if (hypothermiaCount >= 2) {
    criteria.push(`Hypothermia: Temperature < 36°C in ${hypothermiaCount} readings`);
    actions.push('Consider septic shock workup');
    riskScore += 2;
  }

  // === RULE 5: Tachycardia ===
  const highHRCount = recentReadings.filter(r => r.heart_rate && r.heart_rate > 100).length;
  if (highHRCount >= 2) {
    criteria.push(`Sustained tachycardia: HR > 100 bpm in ${highHRCount} of last ${recentReadings.length} readings`);
    riskScore += 1;
  }

  // === RULE 6: Oxygen Desaturation ===
  const lowSpO2Count = recentReadings.filter(r => r.spo2 && r.spo2 < 94).length;
  if (lowSpO2Count >= 2) {
    criteria.push(`Oxygen desaturation: SpO₂ < 94% in ${lowSpO2Count} readings`);
    actions.push('Increase supplemental oxygen');
    actions.push('Prepare for possible intubation if deteriorating');
    riskScore += 2;
  }

  // === RULE 7: WBC Abnormality ===
  if (latestReading.wbc && (latestReading.wbc > 12 || latestReading.wbc < 4)) {
    const abnormality = latestReading.wbc > 12 ? 'Leukocytosis' : 'Leukopenia';
    criteria.push(`${abnormality}: WBC ${latestReading.wbc.toFixed(1)} ×10³/μL`);
    riskScore += 1;
  }

  // === RULE 8: Acute Kidney Injury ===
  if (latestReading.creatinine && latestReading.creatinine > 1.2) {
    criteria.push(`Elevated creatinine: ${latestReading.creatinine.toFixed(2)} mg/dL`);
    actions.push('Monitor urine output');
    actions.push('Consider renal-dose medication adjustments');
    riskScore += latestReading.creatinine > 2 ? 2 : 1;
  }

  // Determine risk level
  let riskLevel = 'LOW';
  if (riskScore >= 6) {
    riskLevel = 'HIGH';
  } else if (riskScore >= 3) {
    riskLevel = 'MODERATE';
  }

  // Add general recommendations based on risk level
  if (riskLevel === 'HIGH' && !actions.includes('Notify attending physician immediately')) {
    actions.unshift('Notify attending physician immediately');
    actions.push('Consider ICU upgrade if in general ward');
  }
  if (riskLevel === 'MODERATE' && !actions.includes('Increase monitoring frequency')) {
    actions.unshift('Increase monitoring frequency to q15min');
  }

  // Generate clinical summary
  const summary = generateClinicalSummary(latestReading, riskLevel, criteria.length);

  return {
    riskLevel,
    criteria,
    actions: actions.slice(0, 5), // Limit to 5 actions
    summary,
    riskScore
  };
}

function generateClinicalSummary(reading, riskLevel, criteriaCount) {
  if (!reading) return 'Awaiting vital signs data';

  const parts = [];

  if (reading.map) parts.push(`MAP ${reading.map} mmHg`);
  if (reading.heart_rate) parts.push(`HR ${reading.heart_rate} bpm`);
  if (reading.respiratory_rate) parts.push(`RR ${reading.respiratory_rate}/min`);
  if (reading.spo2) parts.push(`SpO₂ ${reading.spo2}%`);
  if (reading.lactate) parts.push(`Lactate ${reading.lactate.toFixed(1)} mmol/L`);

  const vitalsStr = parts.join(', ');

  if (riskLevel === 'HIGH') {
    return `Critical: ${criteriaCount} warning criteria triggered. ${vitalsStr}`;
  } else if (riskLevel === 'MODERATE') {
    return `Concerning trends detected. ${vitalsStr}`;
  }
  return `Stable parameters. ${vitalsStr}`;
}

/**
 * Determines patient display status based on risk
 */
export function getPatientStatus(riskLevel) {
  switch (riskLevel) {
    case 'HIGH': return 'Critical';
    case 'MODERATE': return 'Warning';
    default: return 'Stable';
  }
}

/**
 * Should an alert be generated?
 * Only fire alerts for clinically meaningful patterns
 */
export function shouldGenerateAlert(riskAssessment, existingAlerts) {
  // Only generate alerts for MODERATE or HIGH risk
  if (riskAssessment.riskLevel === 'LOW') return false;

  // Check if we have an active alert with same risk level in last 10 minutes
  const recentActiveAlert = existingAlerts.find(alert =>
    alert.is_active &&
    alert.risk_level === riskAssessment.riskLevel &&
    new Date() - new Date(alert.timestamp) < 30 * 60 * 1000
  );

  // Don't spam alerts
  if (recentActiveAlert) return false;

  return true;
}