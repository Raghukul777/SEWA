// Baseline vital sign values per patient trajectory (physiological constants)
const BASE_VITALS = {
  stable: {
    heart_rate: 75,
    respiratory_rate: 16,
    map: 85,
    temperature: 37.0,
    spo2: 98,
    lactate: 1.0,
    wbc: 8.0,
    creatinine: 0.9
  },
  early_sepsis: {
    heart_rate: 88,
    respiratory_rate: 18,
    map: 75,
    temperature: 37.8,
    spo2: 96,
    lactate: 1.5,
    wbc: 11.0,
    creatinine: 1.0
  },
  rapid_deterioration: {
    heart_rate: 95,
    respiratory_rate: 20,
    map: 70,
    temperature: 38.2,
    spo2: 95,
    lactate: 2.0,
    wbc: 14.0,
    creatinine: 1.1
  }
};

/**
 * Generate next vital reading based on patient trajectory
 */
export function generateVitalReading(patient, previousReadings = []) {
  const trajectory = patient.trajectory || 'stable';
  const readingCount = previousReadings.length;

  const base = patient.initial_vitals || BASE_VITALS[trajectory] || BASE_VITALS.stable;

  // Get previous reading for continuity
  const prev = previousReadings.length > 0
    ? previousReadings[previousReadings.length - 1]
    : base;

  // Calculate progression factor (0 to 1 over ~20 readings)
  const progression = Math.min(readingCount / 20, 1);

  // Small random variation
  const jitter = () => (Math.random() - 0.5) * 2;

  let vitals;

  switch (trajectory) {
    case 'stable':
      vitals = {
        heart_rate: Math.round(base.heart_rate + jitter() * 5),
        respiratory_rate: Math.round(base.respiratory_rate + jitter() * 2),
        map: Math.round(base.map + jitter() * 5),
        temperature: +(base.temperature + jitter() * 0.2).toFixed(1),
        spo2: Math.min(100, Math.round(base.spo2 + jitter())),
        lactate: +(base.lactate + jitter() * 0.2).toFixed(1),
        wbc: +(base.wbc + jitter() * 0.5).toFixed(1),
        creatinine: +(base.creatinine + jitter() * 0.05).toFixed(2)
      };
      break;

    case 'early_sepsis':
      // Gradual worsening
      vitals = {
        heart_rate: Math.round(base.heart_rate + progression * 20 + jitter() * 5),
        respiratory_rate: Math.round(base.respiratory_rate + progression * 6 + jitter() * 2),
        map: Math.round(base.map - progression * 15 + jitter() * 3),
        temperature: +(base.temperature + progression * 0.8 + jitter() * 0.2).toFixed(1),
        spo2: Math.max(88, Math.round(base.spo2 - progression * 4 + jitter())),
        lactate: +(base.lactate + progression * 1.5 + jitter() * 0.3).toFixed(1),
        wbc: +(base.wbc + progression * 4 + jitter() * 0.5).toFixed(1),
        creatinine: +(base.creatinine + progression * 0.4 + jitter() * 0.05).toFixed(2)
      };
      break;

    case 'rapid_deterioration':
      // Fast decline
      const fastProgression = Math.min(readingCount / 10, 1);
      vitals = {
        heart_rate: Math.round(base.heart_rate + fastProgression * 30 + jitter() * 8),
        respiratory_rate: Math.round(base.respiratory_rate + fastProgression * 10 + jitter() * 3),
        map: Math.max(50, Math.round(base.map - fastProgression * 25 + jitter() * 4)),
        temperature: +(base.temperature + fastProgression * 1.2 + jitter() * 0.3).toFixed(1),
        spo2: Math.max(85, Math.round(base.spo2 - fastProgression * 8 + jitter() * 2)),
        lactate: +(base.lactate + fastProgression * 3 + jitter() * 0.5).toFixed(1),
        wbc: +(base.wbc + fastProgression * 6 + jitter() * 1).toFixed(1),
        creatinine: +(base.creatinine + fastProgression * 0.8 + jitter() * 0.1).toFixed(2)
      };
      break;

    default:
      vitals = base;
  }

  // Ensure values stay in realistic ranges
  vitals.heart_rate = Math.max(40, Math.min(180, vitals.heart_rate));
  vitals.respiratory_rate = Math.max(8, Math.min(40, vitals.respiratory_rate));
  vitals.map = Math.max(40, Math.min(120, vitals.map));
  vitals.temperature = Math.max(35, Math.min(41, vitals.temperature));
  vitals.spo2 = Math.max(80, Math.min(100, vitals.spo2));
  vitals.lactate = Math.max(0.5, Math.min(10, vitals.lactate));
  vitals.wbc = Math.max(2, Math.min(30, vitals.wbc));
  vitals.creatinine = Math.max(0.5, Math.min(4, vitals.creatinine));

  return {
    patient_id: patient.patient_id,
    timestamp: new Date().toISOString(),
    ...vitals
  };
}

/**
 * Generate initial set of readings for a patient
 */
export function generateInitialReadings(patient, count = 5) {
  const readings = [];
  const now = Date.now();

  for (let i = 0; i < count; i++) {
    const reading = generateVitalReading(patient, readings);
    // Backdate timestamps (5 seconds interval)
    reading.timestamp = new Date(now - (count - 1 - i) * 5000).toISOString();
    readings.push(reading);
  }
  return readings;
}